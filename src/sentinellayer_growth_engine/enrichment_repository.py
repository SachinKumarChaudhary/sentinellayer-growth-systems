from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any, Protocol

import psycopg

from .contact_verification import VerificationResult
from .enrichment_contracts import EnrichmentBatch, EnrichmentPacket, Evidence
from .intent_normalization import normalize_signal
from .intelligence_scoring import score_company


class ConnectionFactory(Protocol):
    def __call__(self) -> psycopg.Connection[Any]:
        ...


class EnrichmentRepository:
    """Persist validated small-batch research packets into canonical schemas."""

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def persist_batch(self, batch: EnrichmentBatch, *, provider: str = "manual_ai_research") -> dict[str, Any]:
        now = datetime.now(UTC)
        results: list[dict[str, Any]] = []
        with self._connection_factory() as conn, conn.cursor() as cur:
            for packet in batch.packets:
                enrichment_run_id = self._start_run(cur, packet, provider, now)
                self._upsert_company_facts(cur, packet, now)
                self._upsert_company_contacts(cur, packet, now)
                decision_maker_ids = self._upsert_decision_makers(cur, packet, now)
                self._insert_packet_evidence(cur, packet, enrichment_run_id, now, decision_maker_ids=decision_maker_ids)
                self._insert_intent_signals(cur, packet, now)
                score = self._upsert_company_score(cur, packet, now)
                self._complete_run(cur, enrichment_run_id, now)
                results.append({"company_id": packet.company_id, "enrichment_run_id": enrichment_run_id, "decision_maker_ids": decision_maker_ids, "score": score})
            conn.commit()
        return {"provider": provider, "results": results}

    @staticmethod
    def _start_run(cur: Any, packet: EnrichmentPacket, provider: str, now: datetime) -> Any:
        cur.execute("""
            INSERT INTO intelligence.enrichment_runs
                (company_id, run_type, provider, status, started_at)
            VALUES (%s, 'company_enrichment', %s, 'running', %s)
            RETURNING enrichment_run_id
            """, (packet.company_id, provider, now))
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("enrichment run insert did not return an id")
        return row[0]

    @staticmethod
    def _complete_run(cur: Any, enrichment_run_id: Any, now: datetime) -> None:
        cur.execute("""
            UPDATE intelligence.enrichment_runs
            SET status = 'completed', completed_at = %s
            WHERE enrichment_run_id = %s
            """, (now, enrichment_run_id))

    @staticmethod
    def _upsert_company_facts(cur: Any, packet: EnrichmentPacket, now: datetime) -> None:
        facts = packet.company_facts
        cur.execute("""
            INSERT INTO intelligence.company_facts
                (company_id, employee_count, monthly_sessions, has_login, vertical,
                 ownership_type, india_bridge, data_sensitivity, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (company_id) DO UPDATE SET
                employee_count = EXCLUDED.employee_count, monthly_sessions = EXCLUDED.monthly_sessions,
                has_login = EXCLUDED.has_login, vertical = EXCLUDED.vertical,
                ownership_type = EXCLUDED.ownership_type, india_bridge = EXCLUDED.india_bridge,
                data_sensitivity = EXCLUDED.data_sensitivity, updated_at = EXCLUDED.updated_at
            """, (packet.company_id, facts.employee_count, facts.monthly_sessions, facts.has_login,
                   facts.vertical, facts.ownership_type, facts.india_bridge, facts.data_sensitivity, now))

    @staticmethod
    def _upsert_company_contacts(cur: Any, packet: EnrichmentPacket, now: datetime) -> None:
        for company_contact in packet.company_contacts:
            cur.execute("""
                INSERT INTO growth.company_contacts
                    (company_id, channel, value, normalized_value, label, source,
                     source_url, confidence, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (company_id, channel, normalized_value) DO UPDATE SET
                    value = EXCLUDED.value, label = EXCLUDED.label,
                    source = EXCLUDED.source, source_url = EXCLUDED.source_url,
                    confidence = EXCLUDED.confidence, updated_at = EXCLUDED.updated_at
                """, (packet.company_id, company_contact.channel, company_contact.value,
                       company_contact.normalized_value, company_contact.label, company_contact.source,
                       company_contact.source_url, company_contact.confidence, now))

    @staticmethod
    def _decision_maker_key(full_name: str, title: str | None) -> str:
        return f"{full_name.casefold()}::{(title or '').casefold()}"

    def _upsert_decision_makers(self, cur: Any, packet: EnrichmentPacket, now: datetime) -> dict[str, Any]:
        ids: dict[str, Any] = {}
        for decision_maker in packet.decision_makers:
            cur.execute("""
                INSERT INTO growth.decision_makers
                    (company_id, full_name, title, role_family, role_priority,
                     rationale, confidence, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (company_id, lower(full_name), lower(coalesce(title, '')))
                DO UPDATE SET title = EXCLUDED.title, role_family = EXCLUDED.role_family,
                    role_priority = EXCLUDED.role_priority, rationale = EXCLUDED.rationale,
                    confidence = EXCLUDED.confidence, updated_at = EXCLUDED.updated_at
                RETURNING decision_maker_id
                """, (packet.company_id, decision_maker.full_name, decision_maker.title,
                       decision_maker.role_family, decision_maker.role_priority, decision_maker.rationale,
                       decision_maker.confidence, now))
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("decision-maker upsert did not return an id")
            decision_maker_id = row[0]
            ids[self._decision_maker_key(decision_maker.full_name, decision_maker.title)] = decision_maker_id
            for contact in decision_maker.contacts:
                cur.execute("""
                    INSERT INTO growth.decision_maker_contact_methods
                        (decision_maker_id, channel, value, normalized_value, source,
                         source_url, verification_status, verification_provider,
                         confidence, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (decision_maker_id, channel, normalized_value) DO UPDATE SET
                        value = EXCLUDED.value, source = EXCLUDED.source,
                        source_url = EXCLUDED.source_url, confidence = EXCLUDED.confidence,
                        updated_at = EXCLUDED.updated_at
                    """, (decision_maker_id, contact.channel, contact.value, contact.normalized_value,
                           contact.source, contact.source_url, contact.verification_status,
                           contact.verification_provider, contact.confidence, now))
        return ids

    @staticmethod
    def _insert_packet_evidence(cur: Any, packet: EnrichmentPacket, enrichment_run_id: Any, now: datetime, *, decision_maker_ids: dict[str, Any] | None = None) -> None:
        decision_maker_ids = decision_maker_ids or {}
        for decision_maker in packet.decision_makers:
            decision_maker_id = decision_maker_ids.get(
                EnrichmentRepository._decision_maker_key(decision_maker.full_name, decision_maker.title)
            )
            for evidence in decision_maker.evidence:
                EnrichmentRepository._insert_evidence(cur, evidence, packet.company_id, enrichment_run_id, now, decision_maker_id=decision_maker_id)
        for company_contact in packet.company_contacts:
            for evidence in company_contact.evidence:
                EnrichmentRepository._insert_evidence(cur, evidence, packet.company_id, enrichment_run_id, now)
        for signal in packet.intent_signals:
            for evidence in signal.evidence:
                EnrichmentRepository._insert_evidence(cur, evidence, packet.company_id, enrichment_run_id, now)

    @staticmethod
    def _insert_evidence(cur: Any, evidence: Evidence, company_id: int, enrichment_run_id: Any, now: datetime, *, decision_maker_id: Any = None) -> None:
        payload = evidence.model_dump(mode="json")
        evidence_hash = EnrichmentRepository._hash_evidence(payload)
        cur.execute("""
            INSERT INTO intelligence.evidence
                (company_id, enrichment_run_id, decision_maker_id, claim_type, claim,
                 source_url, source_type, observed_at, event_date, confidence, evidence_hash)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (evidence_hash) DO NOTHING
            """, (company_id, enrichment_run_id, decision_maker_id, evidence.claim_type,
                   json.dumps(evidence.claim), evidence.source_url, evidence.source_type,
                   evidence.observed_at or now, evidence.event_date, evidence.confidence, evidence_hash))

    @staticmethod
    def _insert_intent_signals(cur: Any, packet: EnrichmentPacket, now: datetime) -> None:
        for signal in packet.intent_signals:
            normalized = normalize_signal(signal_type=signal.signal_type, signal_date=signal.signal_date)
            cur.execute("""
                INSERT INTO intelligence.intent_signals
                    (company_id, signal_type, signal_date, weight, half_life_days,
                     confidence, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (company_id, signal_type, signal_date) DO UPDATE SET
                    detected_at = now(), weight = EXCLUDED.weight,
                    half_life_days = EXCLUDED.half_life_days, confidence = EXCLUDED.confidence,
                    status = 'active'
                """, (packet.company_id, normalized.signal_type, normalized.signal_date,
                       normalized.weight, normalized.half_life_days, signal.confidence, now))

    @staticmethod
    def _upsert_company_score(cur: Any, packet: EnrichmentPacket, now: datetime) -> dict[str, Any]:
        normalized_signals = [normalize_signal(signal_type=signal.signal_type, signal_date=signal.signal_date).as_score_input() for signal in packet.intent_signals]
        notes = "\n".join(packet.research_notes + ([packet.personalization_angle] if packet.personalization_angle else []))
        score = score_company(employee_count=packet.company_facts.employee_count, monthly_sessions=packet.company_facts.monthly_sessions,
                              has_login=packet.company_facts.has_login, notes=notes, signals=normalized_signals,
                              today=now.date(), india_bridge=packet.company_facts.india_bridge)
        cur.execute("""
            INSERT INTO intelligence.company_scores
                (company_id, fit_score, intent_score, behavior_override,
                 negative_flags, modifiers, priority, scored_at, updated_at)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s)
            ON CONFLICT (company_id) DO UPDATE SET fit_score = EXCLUDED.fit_score,
                intent_score = EXCLUDED.intent_score, behavior_override = EXCLUDED.behavior_override,
                negative_flags = EXCLUDED.negative_flags, modifiers = EXCLUDED.modifiers,
                priority = EXCLUDED.priority, scored_at = EXCLUDED.scored_at, updated_at = EXCLUDED.updated_at
            """, (packet.company_id, score.fit_score, score.intent_score, score.behavior_override,
                   json.dumps(score.negative_flags), json.dumps(score.modifiers), score.priority, now, now))
        return score.__dict__

    @staticmethod
    def _hash_evidence(payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def update_contact_verification(cur: Any, decision_maker_id: Any, normalized_value: str, result: VerificationResult, now: datetime | None = None) -> None:
        observed_at = now or datetime.now(UTC)
        cur.execute("""
            UPDATE growth.decision_maker_contact_methods
            SET verification_status = %s, verification_provider = %s,
                confidence = %s, last_verified_at = %s, updated_at = %s
            WHERE decision_maker_id = %s AND normalized_value = %s
            """, (result.status, result.provider, result.confidence, observed_at, observed_at, decision_maker_id, normalized_value))

    def next_enrichment_company_ids(self, limit: int = 40) -> list[int]:
        """Return the next bounded set for the autonomous daily enrichment worker."""
        if not 1 <= limit <= 40:
            raise ValueError("next_enrichment_company_ids limit must be between 1 and 40")
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT c.id FROM public.companies AS c
                WHERE NOT EXISTS (SELECT 1 FROM intelligence.enrichment_runs AS er WHERE er.company_id = c.id AND er.status = 'completed')
                ORDER BY c.id LIMIT %s
                """, (limit,))
            return [row[0] for row in cur.fetchall()]

    def next_refresh_company_ids(self, limit: int = 10, min_age_days: int = 7) -> list[int]:
        """Return completed companies whose latest enrichment is stale enough to refresh."""
        if not 1 <= limit <= 20:
            raise ValueError("next_refresh_company_ids limit must be between 1 and 20")
        if min_age_days < 1:
            raise ValueError("min_age_days must be positive")
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT c.id FROM public.companies AS c
                JOIN LATERAL (
                    SELECT er.completed_at FROM intelligence.enrichment_runs AS er
                    WHERE er.company_id = c.id AND er.status = 'completed'
                    ORDER BY er.completed_at DESC NULLS LAST LIMIT 1
                ) AS latest ON TRUE
                LEFT JOIN intelligence.company_scores AS cs ON cs.company_id = c.id
                WHERE latest.completed_at <= now() - (%s * interval '1 day')
                ORDER BY CASE cs.priority
                    WHEN 'P1' THEN 0 WHEN 'P2' THEN 1 WHEN 'P3' THEN 2 WHEN 'P4' THEN 3 ELSE 4 END,
                    cs.scored_at ASC NULLS FIRST, latest.completed_at ASC
                LIMIT %s
                """, (min_age_days, limit))
            return [row[0] for row in cur.fetchall()]

    def next_companies(self, limit: int = 3) -> list[int]:
        if not 1 <= limit <= 3:
            raise ValueError("next_companies limit must be between 1 and 3")
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT c.id FROM public.companies AS c
                WHERE NOT EXISTS (SELECT 1 FROM intelligence.enrichment_runs AS er WHERE er.company_id = c.id AND er.status = 'completed')
                ORDER BY c.id LIMIT %s
                """, (limit,))
            return [row[0] for row in cur.fetchall()]