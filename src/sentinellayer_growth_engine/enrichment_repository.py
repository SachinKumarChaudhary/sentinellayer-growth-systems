from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Protocol

import psycopg

from .enrichment_contracts import EnrichmentBatch, EnrichmentPacket, Evidence


class ConnectionFactory(Protocol):
    def __call__(self) -> psycopg.Connection[Any]:
        ...


class EnrichmentRepository:
    """Persists validated small-batch research packets into canonical growth schemas."""

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def persist_batch(self, batch: EnrichmentBatch, *, provider: str = "manual_ai_research") -> dict[str, Any]:
        now = datetime.now(UTC)
        results: list[dict[str, Any]] = []
        with self._connection_factory() as conn, conn.cursor() as cur:
            for packet in batch.packets:
                run_id = self._insert_run(cur, packet, provider, now)
                self._upsert_company_contacts(cur, packet, now)

                decision_maker_ids = self._upsert_decision_makers(cur, packet, now)
                self._insert_packet_evidence(cur, packet, decision_maker_ids, run_id)
                self._insert_intent_signals(cur, packet, run_id, now)

                cur.execute(
                    """
                    update intelligence.enrichment_runs
                    set status = 'completed', completed_at = %s
                    where enrichment_run_id = %s
                    """,
                    (now, run_id),
                )
                results.append({"company_id": packet.company_id, "enrichment_run_id": str(run_id)})
        return {"provider": provider, "processed": results}

    def _insert_run(
        self, cur: psycopg.Cursor[Any], packet: EnrichmentPacket, provider: str, now: datetime
    ) -> Any:
        cur.execute(
            """
            insert into intelligence.enrichment_runs (
                company_id, run_type, provider, model_or_agent, status, started_at
            ) values (%s, %s, %s, %s, 'running', %s)
            returning enrichment_run_id
            """,
            (packet.company_id, "small_batch_research", provider, provider, now),
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError("failed to create enrichment run")
        return row[0]

    def _upsert_company_contacts(
        self, cur: psycopg.Cursor[Any], packet: EnrichmentPacket, now: datetime
    ) -> None:
        for contact in packet.company_contacts:
            cur.execute(
                """
                insert into growth.company_contacts (
                    company_id, channel, value, normalized_value, label,
                    source, source_url, verification_status, confidence,
                    first_seen_at
                ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                on conflict (company_id, channel, normalized_value) do update
                set value=excluded.value,
                    label=excluded.label,
                    source=coalesce(excluded.source, growth.company_contacts.source),
                    source_url=coalesce(excluded.source_url, growth.company_contacts.source_url),
                    confidence=greatest(
                        coalesce(growth.company_contacts.confidence, 0),
                        coalesce(excluded.confidence, 0)
                    )
                """,
                (
                    packet.company_id,
                    contact.channel,
                    contact.value,
                    contact.normalized_value,
                    contact.label,
                    contact.source,
                    contact.source_url,
                    "candidate",
                    contact.confidence,
                    now,
                ),
            )

    def _upsert_decision_makers(
        self, cur: psycopg.Cursor[Any], packet: EnrichmentPacket, now: datetime
    ) -> dict[str, Any]:
        ids_by_name: dict[str, Any] = {}
        for dm in packet.decision_makers:
            cur.execute(
                """
                insert into growth.decision_makers (
                    company_id, full_name, title, role_family, role_priority,
                    rationale, confidence, first_seen_at, updated_at,
                    status, research_status
                ) values (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,'candidate','complete'
                )
                on conflict (company_id, lower(full_name), lower(coalesce(title,'')))
                do update set
                    role_family=coalesce(excluded.role_family, growth.decision_makers.role_family),
                    role_priority=coalesce(excluded.role_priority, growth.decision_makers.role_priority),
                    rationale=coalesce(excluded.rationale, growth.decision_makers.rationale),
                    confidence=greatest(
                        coalesce(growth.decision_makers.confidence, 0),
                        coalesce(excluded.confidence, 0)
                    ),
                    updated_at=excluded.updated_at,
                    research_status='complete'
                returning decision_maker_id
                """,
                (
                    packet.company_id,
                    dm.full_name,
                    dm.title,
                    dm.role_family,
                    dm.role_priority,
                    dm.rationale,
                    dm.confidence,
                    now,
                    now,
                ),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError("failed to upsert decision maker")
            decision_maker_id = row[0]
            ids_by_name[dm.full_name.lower()] = decision_maker_id

            for contact in dm.contacts:
                cur.execute(
                    """
                    insert into growth.decision_maker_contact_methods (
                        decision_maker_id, channel, value, normalized_value,
                        source, source_url, verification_status,
                        verification_provider, confidence, first_seen_at, last_verified_at
                    ) values (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                    )
                    on conflict (decision_maker_id, channel, normalized_value) do update
                    set value=excluded.value,
                        source=coalesce(excluded.source, growth.decision_maker_contact_methods.source),
                        source_url=coalesce(excluded.source_url, growth.decision_maker_contact_methods.source_url),
                        confidence=greatest(
                            coalesce(growth.decision_maker_contact_methods.confidence, 0),
                            coalesce(excluded.confidence, 0)
                        )
                    """,
                    (
                        decision_maker_id,
                        contact.channel,
                        contact.value,
                        contact.normalized_value,
                        contact.source,
                        contact.source_url,
                        contact.verification_status,
                        contact.verification_provider,
                        contact.confidence,
                        now,
                        contact.last_verified_at,
                    ),
                )
        return ids_by_name

    def _insert_packet_evidence(
        self,
        cur: psycopg.Cursor[Any],
        packet: EnrichmentPacket,
        decision_maker_ids: dict[str, Any],
        run_id: Any,
    ) -> None:
        for dm in packet.decision_makers:
            for evidence in dm.evidence:
                self._insert_evidence(
                    cur, run_id, packet.company_id, decision_maker_ids[dm.full_name.lower()], evidence
                )
        for contact in packet.company_contacts:
            for evidence in contact.evidence:
                self._insert_evidence(cur, run_id, packet.company_id, None, evidence)
        for signal in packet.intent_signals:
            for evidence in signal.evidence:
                self._insert_evidence(cur, run_id, packet.company_id, None, evidence)

    def _insert_evidence(
        self,
        cur: psycopg.Cursor[Any],
        run_id: Any,
        company_id: int,
        decision_maker_id: Any,
        evidence: Evidence,
    ) -> None:
        observed_at = evidence.observed_at or datetime.now(UTC)
        evidence_hash = self._hash_evidence(evidence.model_dump(mode="json"))
        cur.execute(
            """
            insert into intelligence.evidence (
                enrichment_run_id, company_id, decision_maker_id,
                claim_type, claim, source_url, source_type,
                observed_at, event_date, confidence, evidence_hash
            ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            on conflict (evidence_hash) do nothing
            """,
            (
                run_id,
                company_id,
                decision_maker_id,
                evidence.claim_type,
                json.dumps(evidence.claim),
                evidence.source_url,
                evidence.source_type,
                observed_at,
                evidence.event_date,
                evidence.confidence,
                evidence_hash,
            ),
        )

    def _insert_intent_signals(
        self,
        cur: psycopg.Cursor[Any],
        packet: EnrichmentPacket,
        run_id: Any,
        now: datetime,
    ) -> None:
        for signal in packet.intent_signals:
            evidence_id = None
            if signal.evidence:
                digest = self._hash_evidence(signal.evidence[0].model_dump(mode="json"))
                cur.execute(
                    "select evidence_id from intelligence.evidence where evidence_hash=%s",
                    (digest,),
                )
                row = cur.fetchone()
                evidence_id = row[0] if row else None

            cur.execute(
                """
                insert into intelligence.intent_signals (
                    company_id, signal_type, signal_date, detected_at,
                    weight, half_life_days, evidence_id, confidence, status
                ) values (%s,%s,%s,%s,%s,%s,%s,%s,'active')
                """,
                (
                    packet.company_id,
                    signal.signal_type,
                    signal.signal_date,
                    now,
                    signal.weight,
                    signal.half_life_days,
                    evidence_id,
                    signal.confidence,
                ),
            )

    def next_companies(self, *, limit: int = 3) -> list[dict[str, Any]]:
        if limit not in (1, 2, 3):
            raise ValueError("limit must be between 1 and 3")
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select c.id, c.domain, c.name, c.country, c.city,
                       c.revenue_est, c.visits_est, c.website,
                       c.company_linkedin, c.notes
                from public.companies c
                where not exists (
                    select 1
                    from intelligence.enrichment_runs er
                    where er.company_id = c.id
                      and er.status = 'completed'
                )
                order by c.id
                limit %s
                """,
                (limit,),
            )
            columns = [desc.name for desc in cur.description]
            return [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]

    @staticmethod
    def _hash_evidence(payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
