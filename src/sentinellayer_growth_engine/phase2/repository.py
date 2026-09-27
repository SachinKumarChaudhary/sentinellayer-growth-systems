from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Protocol

import psycopg

from .models import EntityCandidate, EntityComparison, EntityRelationship, EntityResolutionDecision
from .storage import EvaluationResultRecord, Phase2RunRecord, ProviderAttemptRecord, ResearchObservationRecord


class ConnectionFactory(Protocol):
    def __call__(self) -> psycopg.Connection[Any]:
        ...


class Phase2Repository:
    """Persist Phase 2 runs while keeping adjudication/evidence records immutable."""

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def create_run(self, run: Phase2RunRecord) -> Phase2RunRecord:
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO growth.entity_resolution_runs
                    (run_id, request_key, contract_version, matching_version, status,
                     started_at, completed_at, input_count, decision_count,
                     candidate_count, escalation_count, metadata, updated_at)
                VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s::jsonb, now())
                ON CONFLICT (request_key) DO NOTHING
                """,
                (
                    run.run_id,
                    run.request_key,
                    run.contract_version,
                    run.matching_version,
                    run.status,
                    run.started_at,
                    run.completed_at,
                    run.input_count,
                    run.decision_count,
                    run.candidate_count,
                    run.escalation_count,
                    json.dumps(run.metadata),
                ),
            )
            cur.execute(
                """
                SELECT run_id::text, request_key, contract_version, matching_version,
                       status, started_at, completed_at, input_count, decision_count,
                       candidate_count, escalation_count, metadata
                FROM growth.entity_resolution_runs
                WHERE request_key = %s
                """,
                (run.request_key,),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("phase2 run was not persisted")
            persisted = Phase2RunRecord.model_validate(
                {
                    "run_id": row[0],
                    "request_key": row[1],
                    "contract_version": row[2],
                    "matching_version": row[3],
                    "status": row[4],
                    "started_at": row[5],
                    "completed_at": row[6],
                    "input_count": row[7],
                    "decision_count": row[8],
                    "candidate_count": row[9],
                    "escalation_count": row[10],
                    "metadata": row[11],
                }
            )
            if (
                persisted.contract_version != run.contract_version
                or persisted.matching_version != run.matching_version
            ):
                raise ValueError(
                    f"request_key {run.request_key!r} already belongs to a different Phase 2 version"
                )
            conn.commit()
        return persisted

    def persist_resolution(
        self,
        *,
        run_id: str,
        lead_id: str,
        candidates: Sequence[EntityCandidate],
        comparisons: Sequence[EntityComparison],
        relationships: Sequence[EntityRelationship],
        decision: EntityResolutionDecision,
    ) -> bool:
        if decision.lead_id != lead_id:
            raise ValueError("decision lead_id does not match persistence lead_id")

        with self._connection_factory() as conn, conn.cursor() as cur:
            for candidate in candidates:
                payload = candidate.model_dump(mode="json")
                cur.execute(
                    """
                    INSERT INTO growth.entity_resolution_candidates
                        (run_id, candidate_id, lead_id, entity_id, entity_type,
                         canonical_name, canonical_domain, aliases, geography,
                         legal_identifier, official_url, domain_verified,
                         official_corporate_url_match, explicit_official_identity_tie,
                         registered_identity_match, corporate_social_match,
                         parent_relationship_consistent, historical_only,
                         clearly_different_legal_entity, conflicting_authoritative_domain,
                         conflicting_geography, external_provider_relationship,
                         currentness, evidence_refs, origin, candidate_payload)
                    VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s::jsonb,
                            %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb)
                    ON CONFLICT (run_id, candidate_id) DO NOTHING
                    """,
                    (
                        run_id,
                        candidate.candidate_id,
                        lead_id,
                        candidate.entity_id,
                        candidate.entity_type,
                        candidate.canonical_name,
                        candidate.canonical_domain,
                        json.dumps(candidate.aliases),
                        json.dumps(candidate.geography),
                        candidate.legal_identifier,
                        candidate.official_url,
                        candidate.domain_verified,
                        candidate.official_corporate_url_match,
                        candidate.explicit_official_identity_tie,
                        candidate.registered_identity_match,
                        candidate.corporate_social_match,
                        candidate.parent_relationship_consistent,
                        candidate.historical_only,
                        candidate.clearly_different_legal_entity,
                        candidate.conflicting_authoritative_domain,
                        candidate.conflicting_geography,
                        candidate.external_provider_relationship,
                        candidate.currentness,
                        json.dumps(candidate.evidence_refs),
                        candidate.origin,
                        json.dumps(payload),
                    ),
                )

            for comparison in comparisons:
                cur.execute(
                    """
                    INSERT INTO growth.entity_resolution_comparisons
                        (run_id, candidate_id, lead_id, score, signals,
                         hard_negative, eligible_for_match, comparison_payload)
                    VALUES (%s::uuid, %s, %s, %s, %s::jsonb, %s, %s, %s::jsonb)
                    ON CONFLICT (run_id, candidate_id) DO NOTHING
                    """,
                    (
                        run_id,
                        comparison.candidate_id,
                        lead_id,
                        comparison.score,
                        json.dumps([item.model_dump(mode="json") for item in comparison.signals]),
                        comparison.hard_negative,
                        comparison.eligible_for_match,
                        json.dumps(comparison.model_dump(mode="json")),
                    ),
                )

            for relationship in relationships:
                cur.execute(
                    """
                    INSERT INTO growth.entity_resolution_relationships
                        (run_id, relationship_id, lead_id, subject_entity_id, predicate,
                         object_entity_id, function_scope, valid_from, valid_to,
                         currentness, evidence_refs, status, adjudication_reason,
                         relationship_payload)
                    VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s::jsonb, %s, %s, %s::jsonb)
                    ON CONFLICT (run_id, relationship_id) DO NOTHING
                    """,
                    (
                        run_id,
                        relationship.relationship_id,
                        lead_id,
                        relationship.subject_entity_id,
                        relationship.predicate,
                        relationship.object_entity_id,
                        relationship.function_scope,
                        relationship.valid_from,
                        relationship.valid_to,
                        relationship.currentness,
                        json.dumps(relationship.evidence_refs),
                        relationship.status,
                        relationship.adjudication_reason,
                        json.dumps(relationship.model_dump(mode="json")),
                    ),
                )

            cur.execute(
                """
                INSERT INTO growth.entity_resolution_decisions
                    (run_id, decision_id, lead_id, contract_version, status,
                     canonical_entity_id, entity_type, canonical_name,
                     canonical_domain, confidence, decisive_signals,
                     rejected_candidates, evidence_refs, currentness,
                     research_required, research_missions, unresolved_questions,
                     matching_version, decided_at, decision_payload)
                VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s::jsonb,
                        %s::jsonb, %s, %s, %s::jsonb)
                ON CONFLICT (run_id, decision_id) DO NOTHING
                """,
                (
                    run_id,
                    decision.decision_id,
                    lead_id,
                    decision.contract_version,
                    decision.status,
                    decision.canonical_entity_id,
                    decision.entity_type,
                    decision.canonical_name,
                    decision.canonical_domain,
                    decision.confidence,
                    json.dumps(decision.decisive_signals),
                    json.dumps(decision.rejected_candidates),
                    json.dumps(decision.evidence_refs),
                    decision.currentness,
                    decision.research_required,
                    json.dumps(decision.research_missions),
                    json.dumps(decision.unresolved_questions),
                    decision.matching_version,
                    decision.decided_at,
                    json.dumps(decision.model_dump(mode="json")),
                ),
            )
            decision_inserted = cur.rowcount == 1

            for trace_no, event in enumerate(decision.decision_trace):
                cur.execute(
                    """
                    INSERT INTO growth.entity_resolution_decision_traces
                        (run_id, decision_id, trace_no, step, detail, candidate_id)
                    VALUES (%s::uuid, %s, %s, %s, %s, %s)
                    ON CONFLICT (run_id, decision_id, trace_no) DO NOTHING
                    """,
                    (
                        run_id,
                        decision.decision_id,
                        trace_no,
                        event.step,
                        event.detail,
                        event.candidate_id,
                    ),
                )

            if decision_inserted:
                cur.execute(
                    """
                    UPDATE growth.entity_resolution_runs
                    SET input_count = input_count + 1,
                        decision_count = decision_count + 1,
                        candidate_count = candidate_count + %s,
                        escalation_count = escalation_count
                            + CASE WHEN %s THEN 1 ELSE 0 END,
                        updated_at = now()
                    WHERE run_id = %s::uuid
                    """,
                    (len(candidates), decision.research_required, run_id),
                )

            conn.commit()
        return decision_inserted

    def persist_provider_attempt(self, attempt: ProviderAttemptRecord) -> None:
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO growth.entity_resolution_provider_attempts
                    (attempt_id, run_id, lead_id, mission_id, provider, operation,
                     request_fingerprint, request_payload, status,
                     provider_request_id, http_status, retry_count, result_count,
                     latency_ms, cost_units, error_code, error_message,
                     quota_state, raw_artifact_ref, raw_artifact_hash,
                     evidence_ids, escalation_reason, information_gain_estimate,
                     started_at, completed_at, metadata)
                VALUES (gen_random_uuid(), %s::uuid, %s, %s, %s, %s, %s,
                        %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s::jsonb, %s, %s, %s::jsonb, %s, %s, %s, %s,
                        %s::jsonb)
                """,
                (
                    attempt.run_id,
                    attempt.lead_id,
                    attempt.mission_id,
                    attempt.provider,
                    attempt.operation,
                    attempt.request_fingerprint,
                    json.dumps(attempt.request_payload),
                    attempt.status,
                    attempt.provider_request_id,
                    attempt.http_status,
                    attempt.retry_count,
                    attempt.result_count,
                    attempt.latency_ms,
                    attempt.cost_units,
                    attempt.error_code,
                    attempt.error_message,
                    json.dumps(attempt.quota_state),
                    attempt.raw_artifact_ref,
                    attempt.raw_artifact_hash,
                    json.dumps(attempt.evidence_ids),
                    attempt.escalation_reason,
                    attempt.information_gain_estimate,
                    attempt.started_at,
                    attempt.completed_at,
                    json.dumps(attempt.metadata),
                ),
            )
            conn.commit()

    def persist_research_observation(self, observation: ResearchObservationRecord) -> None:
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO growth.entity_resolution_research_observations
                    (run_id, observation_id, mission_id, provider, observation_type,
                     result_position, url, final_url, source_domain, title, snippet,
                     text_content, published_at, observed_at, request_params,
                     provenance, search_linked, observation_payload)
                VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb)
                ON CONFLICT (run_id, observation_id) DO NOTHING
                """,
                (
                    observation.run_id,
                    observation.observation_id,
                    observation.mission_id,
                    observation.provider,
                    observation.observation_type,
                    observation.result_position,
                    observation.url,
                    observation.final_url,
                    observation.source_domain,
                    observation.title,
                    observation.snippet,
                    observation.text_content,
                    observation.published_at,
                    observation.observed_at,
                    json.dumps(observation.request_params),
                    json.dumps(observation.provenance),
                    observation.search_linked,
                    json.dumps(observation.observation_payload),
                ),
            )
            conn.commit()

    def persist_evaluation(self, result: EvaluationResultRecord) -> None:
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO growth.entity_resolution_evaluation_results
                    (run_id, benchmark_version, case_id, entity_type_score,
                     ownership_score, operating_entity_score, relationship_score,
                     functional_control_score, currentness_score,
                     evidence_quality_score, false_positive_safety_score,
                     total_score, critical_failure, passed, expected_payload,
                     observed_payload, evaluator_version)
                VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                ON CONFLICT (run_id, benchmark_version, case_id) DO NOTHING
                """,
                (
                    result.run_id,
                    result.benchmark_version,
                    result.case_id,
                    result.entity_type_score,
                    result.ownership_score,
                    result.operating_entity_score,
                    result.relationship_score,
                    result.functional_control_score,
                    result.currentness_score,
                    result.evidence_quality_score,
                    result.false_positive_safety_score,
                    result.total_score,
                    result.critical_failure,
                    result.passed,
                    json.dumps(result.expected_payload),
                    json.dumps(result.observed_payload),
                    result.evaluator_version,
                ),
            )
            conn.commit()

    def complete_run(
        self,
        *,
        run_id: str,
        status: str,
        completed_at: datetime,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if status not in {"COMPLETED", "FAILED", "CANCELLED"}:
            raise ValueError(f"invalid terminal status: {status}")
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE growth.entity_resolution_runs
                SET status = %s,
                    completed_at = %s,
                    metadata = CASE
                        WHEN %s::jsonb = '{}'::jsonb THEN metadata
                        ELSE %s::jsonb
                    END,
                    updated_at = now()
                WHERE run_id = %s::uuid
                """,
                (
                    status,
                    completed_at,
                    json.dumps(metadata or {}),
                    json.dumps(metadata or {}),
                    run_id,
                ),
            )
            if cur.rowcount != 1:
                raise ValueError(f"unknown phase2 run: {run_id}")
            conn.commit()
