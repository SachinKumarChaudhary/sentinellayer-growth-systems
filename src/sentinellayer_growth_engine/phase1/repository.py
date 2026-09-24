from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Protocol

import psycopg

from .models import (
    CanonicalLead,
    DuplicateDecision,
    FieldObservation,
    Phase1Handoff,
    Phase1Result,
    ValidationFinding,
)


class ConnectionFactory(Protocol):
    def __call__(self) -> psycopg.Connection[Any]:
        ...


class Phase1Repository:
    """Persist Phase 1 observations and projections without mutating raw evidence."""

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def list_source_records(self) -> list[LeadSourceRecord]:
        """Load immutable source observations for deterministic exact-dedupe adjudication."""
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT source_record_id, schema_version, source_name, source_version,
                       source_record_key, acquired_at, source_payload, mapped_fields,
                       raw_fingerprint, adapter_version
                FROM growth.lead_source_records
                ORDER BY received_at, source_record_id
                """
            )
            rows = cur.fetchall()
        return [LeadSourceRecord.model_validate({
            "source_record_id": row[0],
            "schema_version": row[1],
            "source_name": row[2],
            "source_version": row[3],
            "source_record_key": row[4],
            "acquired_at": row[5],
            "source_payload": row[6],
            "mapped_fields": row[7],
            "raw_fingerprint": row[8],
            "adapter_version": row[9],
        }) for row in rows]

    def persist_result(self, result: Phase1Result) -> dict[str, Any]:
        source = result.source_record
        now = datetime.now(UTC)
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT raw_fingerprint
                FROM growth.lead_source_records
                WHERE source_record_id = %s
                """,
                (source.source_record_id,),
            )
            existing_source = cur.fetchone()
            if existing_source is not None:
                if existing_source[0] != source.raw_fingerprint:
                    raise ValueError(
                        f"source_record_id collision for {source.source_record_id}"
                    )
                cur.execute(
                    """
                    SELECT state
                    FROM growth.lead_processing_state
                    WHERE source_record_id = %s
                    """,
                    (source.source_record_id,),
                )
                existing_state = cur.fetchone()
                if existing_state is not None and existing_state[0] in {
                    "ACCEPTED",
                    "ACCEPTED_WITH_WARNINGS",
                    "DUPLICATE",
                }:
                    conn.commit()
                    return {
                        "source_record_id": source.source_record_id,
                        "state": "REPLAY_NOOP",
                        "lead_id": result.canonical_lead.lead_id
                        if result.canonical_lead
                        else None,
                    }

            cur.execute(
                """
                INSERT INTO growth.lead_source_records
                    (source_record_id, schema_version, source_name, source_version,
                     source_record_key, acquired_at, source_payload, mapped_fields,
                     raw_fingerprint, adapter_version)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
                ON CONFLICT (source_record_id) DO NOTHING
                """,
                (
                    source.source_record_id,
                    source.schema_version,
                    source.source_name,
                    source.source_version,
                    source.source_record_key,
                    source.acquired_at,
                    json.dumps(source.source_payload),
                    json.dumps([item.model_dump(mode="json") for item in source.mapped_fields]),
                    source.raw_fingerprint,
                    source.adapter_version,
                ),
            )

            cur.execute(
                """
                INSERT INTO growth.lead_processing_state
                    (source_record_id, state, lead_id, quality_status, contract_version,
                     validation_version, normalization_version, processed_at, last_error,
                     retry_count, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s)
                ON CONFLICT (source_record_id) DO UPDATE SET
                    state = EXCLUDED.state,
                    lead_id = EXCLUDED.lead_id,
                    quality_status = EXCLUDED.quality_status,
                    contract_version = EXCLUDED.contract_version,
                    validation_version = EXCLUDED.validation_version,
                    normalization_version = EXCLUDED.normalization_version,
                    processed_at = EXCLUDED.processed_at,
                    last_error = EXCLUDED.last_error,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    source.source_record_id,
                    result.state,
                    result.canonical_lead.lead_id if result.canonical_lead else None,
                    result.canonical_lead.quality_status if result.canonical_lead else None,
                    result.handoff.contract_version if result.handoff else "v1",
                    result.findings[0].validation_version if result.findings else None,
                    result.canonical_lead.normalization_version
                    if result.canonical_lead
                    else None,
                    now if result.state != "RECEIVED" else None,
                    None,
                    now,
                ),
            )

            self._insert_observations(cur, result.canonical_lead.field_observations if result.canonical_lead else [])
            self._insert_findings(cur, result.findings)
            self._insert_duplicate_decision(cur, result.duplicate_decision)

            if result.canonical_lead is not None:
                self._upsert_canonical_projection(cur, result.canonical_lead)

            if result.state == "QUARANTINED":
                self._upsert_quarantine(cur, result)
            elif result.state in {"ACCEPTED", "ACCEPTED_WITH_WARNINGS"}:
                self._resolve_quarantine(cur, source.source_record_id)

            if result.handoff is not None:
                self._insert_handoff(cur, result.handoff)

            conn.commit()

        return {
            "source_record_id": source.source_record_id,
            "state": result.state,
            "lead_id": result.canonical_lead.lead_id if result.canonical_lead else None,
        }

    @staticmethod
    def _insert_observations(cur: Any, observations: list[FieldObservation]) -> None:
        for item in observations:
            cur.execute(
                """
                INSERT INTO growth.lead_field_observations
                    (observation_id, lead_id, source_record_id, field, source_field_name,
                     raw_value, normalized_value, value_state, observed_at, adapter_version,
                     normalization_version, transformation_reason)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s)
                ON CONFLICT (observation_id) DO NOTHING
                """,
                (
                    item.observation_id,
                    item.lead_id,
                    item.source_record_id,
                    item.field,
                    item.source_field_name,
                    json.dumps(item.raw_value),
                    json.dumps(item.normalized_value),
                    item.value_state,
                    item.observed_at,
                    item.adapter_version,
                    item.normalization_version,
                    item.transformation_reason,
                ),
            )

    @staticmethod
    def _insert_findings(cur: Any, findings: list[ValidationFinding]) -> None:
        for item in findings:
            cur.execute(
                """
                INSERT INTO growth.lead_validation_findings
                    (finding_id, source_record_id, lead_id, field, rule_id, severity,
                     code, message, observed_value_ref, created_at, validation_version)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (finding_id) DO NOTHING
                """,
                (
                    item.finding_id,
                    item.source_record_id,
                    item.lead_id,
                    item.field,
                    item.rule_id,
                    item.severity,
                    item.code,
                    item.message,
                    item.observed_value_ref,
                    item.created_at,
                    item.validation_version,
                ),
            )

    @staticmethod
    def _insert_duplicate_decision(cur: Any, item: DuplicateDecision) -> None:
        cur.execute(
            """
            INSERT INTO growth.lead_duplicate_decisions
                (decision_id, source_record_id, duplicate_type, rule_id,
                 matched_source_record_ids, comparison_keys, decided_at, decision_version)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
            ON CONFLICT (decision_id) DO NOTHING
            """,
            (
                item.decision_id,
                item.source_record_id,
                item.duplicate_type,
                item.rule_id,
                json.dumps(item.matched_source_record_ids),
                json.dumps(item.comparison_keys),
                item.decided_at,
                item.decision_version,
            ),
        )

    @staticmethod
    def _upsert_canonical_projection(cur: Any, lead: CanonicalLead) -> None:
        cur.execute(
            """
            INSERT INTO growth.lead_canonical_projection
                (lead_id, display_name, legal_name, domain, canonical_url, country_code,
                 region, city, postal_code, platform, source_refs, normalization_version,
                 raw_fingerprint, source_fingerprint, canonical_fingerprint, quality_status,
                 quality_finding_ids, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s,
                    %s, %s::jsonb, %s, %s)
            ON CONFLICT (lead_id) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                legal_name = EXCLUDED.legal_name,
                domain = EXCLUDED.domain,
                canonical_url = EXCLUDED.canonical_url,
                country_code = EXCLUDED.country_code,
                region = EXCLUDED.region,
                city = EXCLUDED.city,
                postal_code = EXCLUDED.postal_code,
                platform = EXCLUDED.platform,
                source_refs = EXCLUDED.source_refs,
                normalization_version = EXCLUDED.normalization_version,
                raw_fingerprint = EXCLUDED.raw_fingerprint,
                source_fingerprint = EXCLUDED.source_fingerprint,
                canonical_fingerprint = EXCLUDED.canonical_fingerprint,
                quality_status = EXCLUDED.quality_status,
                quality_finding_ids = EXCLUDED.quality_finding_ids,
                updated_at = EXCLUDED.updated_at
            """,
            (
                lead.lead_id,
                lead.display_name,
                lead.legal_name,
                lead.domain,
                lead.canonical_url,
                lead.country_code,
                lead.region,
                lead.city,
                lead.postal_code,
                lead.platform,
                json.dumps(lead.source_refs),
                lead.normalization_version,
                lead.raw_fingerprint,
                lead.source_fingerprint,
                lead.canonical_fingerprint,
                lead.quality_status,
                json.dumps(lead.quality_finding_ids),
                lead.created_at,
                lead.updated_at,
            ),
        )

    @staticmethod
    def _upsert_quarantine(cur: Any, result: Phase1Result) -> None:
        lead_id = result.canonical_lead.lead_id if result.canonical_lead else None
        cur.execute(
            """
            INSERT INTO growth.lead_quarantine
                (source_record_id, lead_id, finding_ids, retry_count, updated_at)
            VALUES (%s, %s, %s::jsonb, 0, now())
            ON CONFLICT (source_record_id) DO UPDATE SET
                lead_id = EXCLUDED.lead_id,
                finding_ids = EXCLUDED.finding_ids,
                updated_at = now()
            """,
            (
                result.source_record.source_record_id,
                lead_id,
                json.dumps([item.finding_id for item in result.findings]),
            ),
        )

    @staticmethod
    def _resolve_quarantine(cur: Any, source_record_id: str) -> None:
        cur.execute(
            """
            UPDATE growth.lead_quarantine
            SET resolved_at = now(), updated_at = now()
            WHERE source_record_id = %s AND resolved_at IS NULL
            """,
            (source_record_id,),
        )

    @staticmethod
    def _insert_handoff(cur: Any, handoff: Phase1Handoff) -> None:
        cur.execute(
            """
            INSERT INTO growth.lead_phase1_handoffs
                (lead_id, canonical_fingerprint, contract_version, quality_status,
                 downstream_eligible, handoff_payload, completed_at)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
            ON CONFLICT (lead_id, canonical_fingerprint) DO NOTHING
            """,
            (
                handoff.lead_id,
                handoff.canonical_fingerprint,
                handoff.contract_version,
                handoff.quality_status,
                handoff.downstream_eligible,
                json.dumps(handoff.model_dump(mode="json")),
                handoff.completed_at,
            ),
        )
