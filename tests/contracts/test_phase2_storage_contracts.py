from __future__ import annotations

from pathlib import Path

MIGRATION = Path("supabase/migrations/20260927160734_phase2_entity_resolution_storage.sql")


def _sql() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_phase2_storage_tables_and_immutability_are_declared() -> None:
    sql = _sql()
    required_tables = (
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
    for table in required_tables:
        assert f"CREATE TABLE IF NOT EXISTS growth.{table}" in sql

    immutable_tables = (
        "entity_resolution_candidates",
        "entity_resolution_comparisons",
        "entity_resolution_relationships",
        "entity_resolution_decisions",
        "entity_resolution_decision_traces",
        "entity_resolution_provider_attempts",
        "entity_resolution_research_observations",
        "entity_resolution_evaluation_results",
    )
    for table in immutable_tables:
        assert f"CREATE TRIGGER {table}_immutable" in sql

    assert "ALTER TABLE growth.entity_resolution_runs ENABLE ROW LEVEL SECURITY;" in sql
    assert "ALTER TABLE growth.entity_resolution_evaluation_results ENABLE ROW LEVEL SECURITY;" in sql


def test_phase2_storage_preserves_exact_contract_payloads_and_versioning() -> None:
    sql = _sql()
    assert "candidate_payload jsonb NOT NULL" in sql
    assert "comparison_payload jsonb NOT NULL" in sql
    assert "relationship_payload jsonb NOT NULL" in sql
    assert "decision_payload jsonb NOT NULL" in sql
    assert "observation_payload jsonb NOT NULL" in sql
    assert "expected_payload jsonb NOT NULL" in sql
    assert "observed_payload jsonb NOT NULL" in sql
    assert "contract_version text NOT NULL" in sql
    assert "matching_version text NOT NULL" in sql


def test_phase2_storage_has_idempotency_and_evaluation_keys() -> None:
    sql = _sql()
    assert "request_key text NOT NULL UNIQUE" in sql
    assert "PRIMARY KEY (run_id, candidate_id)" in sql
    assert "PRIMARY KEY (run_id, decision_id)" in sql
    assert "UNIQUE (run_id, lead_id)" in sql
    assert "UNIQUE (run_id, benchmark_version, case_id)" in sql
