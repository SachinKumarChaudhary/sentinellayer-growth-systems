from __future__ import annotations

import os
from uuid import uuid4

import psycopg
import pytest


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
