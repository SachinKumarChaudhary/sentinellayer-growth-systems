from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any, Self
from uuid import uuid4

import psycopg
import pytest

from sentinellayer_growth_engine.phase2.models import (
    ComparisonSignal,
    DecisionTraceEvent,
    EntityCandidate,
    EntityComparison,
    EntityResolutionDecision,
)
from sentinellayer_growth_engine.phase2.repository import Phase2Repository
from sentinellayer_growth_engine.phase2.storage import Phase2RunRecord


PHASE2_TABLES = (
    "entity_resolution_runs",
    "entity_resolution_candidates",
    "entity_resolution_comparisons",
    "entity_resolution_relationships",
    "entity_resolution_decisions",
    "entity_resolution_decision_traces",
    "entity_resolution_provider_attempts",
    "entity_resolution_research_observations",
    "entity_resolution_evaluation_results",
)


@pytest.mark.integration
def test_phase2_storage_schema_and_immutability() -> None:
    dsn = os.environ.get("SUPABASE_DATABASE_URL")
    if not dsn:
        pytest.skip("SUPABASE_DATABASE_URL is required for integration tests")

    run_id = uuid4()
    candidate_id = f"ci-candidate-{uuid4().hex}"
    try:
        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute(
                """
                select table_name
                from information_schema.tables
                where table_schema = 'growth'
                  and table_name = any(%s)
                """,
                (list(PHASE2_TABLES),),
            )
            assert {row[0] for row in cur.fetchall()} == set(PHASE2_TABLES)

            cur.execute(
                """
                select c.relname
                from pg_class c
                join pg_namespace n on n.oid = c.relnamespace
                where n.nspname = 'growth'
                  and c.relname = any(%s)
                  and c.relrowsecurity = true
                """,
                (list(PHASE2_TABLES),),
            )
            assert {row[0] for row in cur.fetchall()} == set(PHASE2_TABLES)

            cur.execute(
                """
                insert into growth.entity_resolution_runs
                    (run_id, request_key, contract_version, matching_version, started_at)
                values (%s, %s, 'phase2.entity_resolution.v1',
                        'phase2.deterministic_match.v1', now())
                """,
                (run_id, f"ci-phase2-storage-{uuid4().hex}"),
            )
            cur.execute(
                """
                insert into growth.entity_resolution_candidates
                    (run_id, candidate_id, lead_id, entity_type, canonical_name,
                     currentness, origin, candidate_payload)
                values (%s, %s, 'ci-lead', 'LEGAL_ENTITY', 'CI Entity',
                        'CURRENT', 'gold', '{}'::jsonb)
                """,
                (run_id, candidate_id),
            )

            with pytest.raises(Exception, match="phase2 immutable table"):
                cur.execute(
                    """
                    update growth.entity_resolution_candidates
                    set canonical_name = 'Mutated'
                    where run_id = %s and candidate_id = %s
                    """,
                    (run_id, candidate_id),
                )
            conn.rollback()
    finally:
        # The transaction is never committed, so all disposable rows are rolled back.
        pass


class _NoCommitConnection:
    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self._connection = connection

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def cursor(self, *args: Any, **kwargs: Any) -> Any:
        return self._connection.cursor(*args, **kwargs)

    def commit(self) -> None:
        return None


class _TransactionalFactory:
    def __init__(self, dsn: str) -> None:
        self.connection = psycopg.connect(dsn)

    def __call__(self) -> _NoCommitConnection:
        return _NoCommitConnection(self.connection)

    def rollback_and_close(self) -> None:
        self.connection.rollback()
        self.connection.close()


@pytest.mark.integration
def test_phase2_repository_persists_and_replays_without_duplication() -> None:
    dsn = os.environ.get("SUPABASE_DATABASE_URL")
    if not dsn:
        pytest.skip("SUPABASE_DATABASE_URL is required for integration tests")

    factory = _TransactionalFactory(dsn)
    run_id = str(uuid4())
    now = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)
    try:
        repository = Phase2Repository(factory)
        repository.create_run(
            Phase2RunRecord(
                run_id=run_id,
                request_key=f"ci-phase2-repository-{uuid4().hex}",
                contract_version="phase2.entity_resolution.v1",
                matching_version="phase2.deterministic_match.v1",
                started_at=now,
            )
        )

        candidate = EntityCandidate(
            candidate_id="candidate-1",
            entity_id="entity-1",
            entity_type="LEGAL_ENTITY",
            canonical_name="CI Entity",
            canonical_domain="ci.example",
            domain_verified=True,
            currentness="CURRENT",
            evidence_refs=["https://ci.example/about"],
            origin="gold",
        )
        comparison = EntityComparison(
            candidate_id="candidate-1",
            score=100,
            signals=[
                ComparisonSignal(
                    code="exact_verified_canonical_domain",
                    strength="strong",
                    weight=100,
                    value=True,
                    reason="Exact verified domain matches the Phase 1 lead.",
                )
            ],
            eligible_for_match=True,
        )
        decision = EntityResolutionDecision(
            decision_id="decision-1",
            lead_id="ci-lead",
            status="MATCHED",
            canonical_entity_id="entity-1",
            entity_type="LEGAL_ENTITY",
            canonical_name="CI Entity",
            canonical_domain="ci.example",
            confidence="high",
            decisive_signals=["exact_verified_canonical_domain"],
            evidence_refs=["https://ci.example/about"],
            currentness="CURRENT",
            decision_trace=[
                DecisionTraceEvent(
                    step="deterministic_match",
                    detail="Exact verified canonical domain established identity.",
                    candidate_id="candidate-1",
                )
            ],
            matching_version="phase2.deterministic_match.v1",
            decided_at=now,
        )

        assert repository.persist_resolution(
            run_id=run_id,
            lead_id="ci-lead",
            candidates=[candidate],
            comparisons=[comparison],
            relationships=[],
            decision=decision,
        )
        assert not repository.persist_resolution(
            run_id=run_id,
            lead_id="ci-lead",
            candidates=[candidate],
            comparisons=[comparison],
            relationships=[],
            decision=decision,
        )

        with factory.connection.cursor() as cur:
            cur.execute(
                """
                select input_count, decision_count, candidate_count
                from growth.entity_resolution_runs
                where run_id = %s
                """,
                (run_id,),
            )
            assert cur.fetchone() == (1, 1, 1)
            cur.execute(
                """
                select count(*) from growth.entity_resolution_candidates
                where run_id = %s
                """,
                (run_id,),
            )
            assert cur.fetchone() == (1,)
            cur.execute(
                """
                select count(*) from growth.entity_resolution_decisions
                where run_id = %s
                """,
                (run_id,),
            )
            assert cur.fetchone() == (1,)
    finally:
        factory.rollback_and_close()
