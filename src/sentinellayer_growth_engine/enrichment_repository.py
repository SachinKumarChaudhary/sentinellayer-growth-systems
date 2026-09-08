from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Protocol

import psycopg

from .enrichment_contracts import EnrichmentBatch, EnrichmentPacket


class ConnectionFactory(Protocol):
    def __call__(self) -> psycopg.Connection[Any]:
        ...


class EnrichmentRepository:
    """Persists validated small-batch research packets into the canonical growth schemas."""

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def persist_batch(self, batch: EnrichmentBatch, *, provider: str = "manual_ai_research") -> dict[str, Any]:
        now = datetime.now(UTC)
        results: list[dict[str, Any]] = []
        with self._connection_factory() as conn, conn.cursor() as cur:
            for packet in batch.packets:
                run_id = self._insert_run(cur, packet, provider, now)
                for evidence in self._evidence_for_packet(packet):
                    cur.execute(
                        """
                        insert into intelligence.evidence (
                            enrichment_run_id, company_id, decision_maker_id,
                            claim_type, claim, source_url, source_type,
                            observed_at, event_date, confidence, evidence_hash
                        ) values (
                            %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s
                        )
                        on conflict (evidence_hash) do nothing
                        """,
                        (
                            run_id,
                            packet.company_id,
                            evidence["decision_maker_id"],
                            evidence["claim_type"],
                            json.dumps(evidence["claim"]),
                            evidence["source_url"],
                            evidence["source_type"],
                            evidence["observed_at"],
                            evidence["event_date"],
                            evidence["confidence"],
                            evidence["evidence_hash"],
                        ),
                    )
                self._upsert_company_contacts(cur, packet, now)
                decision_maker_ids = self._upsert_decision_makers(cur, packet, now)
                self._upsert_intent_signals(cur, packet, decision_maker_ids, run_id, now)
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

    def _insert_run(self, cur: psycopg.Cursor[Any], packet: EnrichmentPacket, provider: str, now: datetime):
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

    def _upsert_company_contacts(self, cur: psycopg.Cursor[Any], packet: EnrichmentPacket, now: datetime) -> None:
        for contact in packet.company_contacts:
            cur.execute(
                """
                insert into growth.company_contacts (
                    company_id, channel, value, normalized_value, label,
                    source, source_url, verification_status, confidence,
                    first_seen_at, last_verified_at
                ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                on conflict (company_id, channel, normalized_value) do update
                set value=excluded.value,
                    label=excluded.label,
                    source=coalesce(excluded.source, growth.company_contacts.source),
                    source_url=coalesce(excluded.source_url, growth.company_contacts.source_url),
                    confidence=greatest(
                        coalesce(growth.company_contacts.confidence, 0),
                        coalesce(excluded.confidence, 0)
                    ),
                    last_verified_at=coalesce(excluded.last_verified_at, growth.company_contacts.last_verified_at)
                """,
                (
                    packet.company_id,
                    contact.channel,
                    contact.value,
                    contact.normalized_value,
                    contact.label,
                    contact.source,
                    contact.source_url,
                    contact.verification_status,
                    contact.confidence,
                    now,
                    None,
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
                    rationale, confidence, first_seen_at, last_verified_at,
                    updated_at, status, research_status
                ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'candidate','complete')
                on conflict (company_id, lower(full_name), lower(coalesce(title,'')))
                do update set
                    role_family=coalesce(excluded.role_family, growth.decision_makers.role_family),
                    role_priority=coalesce(excluded.role_priority, growth.decision_makers.role_priority),
                    rationale=coalesce(excluded.rationale, growth.decision_makers.rationale),
                    confidence=greatest(
                        coalesce(growth.decision_makers.confidence, 0),
                        coalesce(excluded.confidence, 0)
                    ),
                    updated_at=excluded.updated_at
                returning decision_maker_id
                """,
                (
                    packet.company_id, dm.full_name, dm.title, dm.role_family,
                    dm.role_priority, dm.rationale, dm.confidence, now, None, now,
                ),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError("failed to upsert decision maker")
            ids_by_name[dm.full_name.lower()] = row[0]
            for contact in dm.contacts:
                cur.execute(
                    """
                    insert into growth.decision_maker_contact_methods (
                        decision_maker_id, channel, value, normalized_value,
                        source, source_url, verification_status,
                        verification_provider, confidence, first_seen_at, last_verified_at
                    ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
                        row[0], contact.channel, contact.value, contact.normalized_value,
                        contact.source, contact.source_url, contact.verification_status,
                        contact.verification_provider, contact.confidence, now, contact.last_verified_at,
                    ),
                )
        return ids_by_name

    def _upsert_intent_signals(
        self,
        cur: psycopg.Cursor[Any],
        packet: EnrichmentPacket,
        decision_maker_ids: dict[str, Any],
        run_id: Any,
        now: datetime,
    ) -> None:
        del decision_maker_ids
        for signal in packet.intent_signals:
            evidence_id = None
            if signal.evidence:
                evidence_hash = self._hash_evidence(signal.evidence[0].model_dump(mode="json"))
                cur.execute(
                    "select evidence_id from intelligence.evidence where evidence_hash=%s",
                    (evidence_hash,),
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
                    packet.company_id, signal.signal_type, signal.signal_date, now,
                    signal.weight, signal.half_life_days, evidence_id, signal.confidence,
                ),
            )

    def _evidence_for_packet(self, packet: EnrichmentPacket) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for dm in packet.decision_makers:
            for evidence in dm.evidence:
                rows.append(self._evidence_row(packet, dm.full_name, evidence))
        for contact in packet.company_contacts:
            for evidence in contact.evidence:
                rows.append(self._evidence_row(packet, None, evidence))
        for signal in packet.intent_signals:
            for evidence in signal.evidence:
                rows.append(self._evidence_row(packet, None, evidence))
        return rows

    @staticmethod
    def _evidence_row(packet: EnrichmentPacket, dm_name: str | None, evidence: Any) -> dict[str, Any]:
        digest = EnrichmentRepository._hash_evidence(evidence.model_dump(mode="json"))
        return {
            "decision_maker_id": None,
            "claim_type": evidence.claim_type,
            "claim": evidence.claim,
            "source_url": evidence.source_url,
            "source_type": evidence.source_type,
            "observed_at": evidence.observed_at or datetime.now(UTC),
            "event_date": evidence.event_date,
            "confidence": evidence.confidence,
            "evidence_hash": digest,
            "_dm_name": dm_name,
        }

    @staticmethod
    def _hash_evidence(payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
