from __future__ import annotations

from pathlib import Path

MIGRATION = Path("supabase/migrations/20260924010000_phase1_lead_intake_storage.sql")


def _sql() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_phase1_storage_has_immutable_observation_tables() -> None:
    sql = _sql()
    for table in (
        "growth.lead_source_records",
        "growth.lead_field_observations",
        "growth.lead_validation_findings",
        "growth.lead_duplicate_decisions",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in sql
        assert f"BEFORE UPDATE OR DELETE ON {table}" in sql


def test_phase1_storage_separates_mutable_processing_state() -> None:
    sql = _sql()
    assert "growth.lead_processing_state" in sql
    assert "ON CONFLICT (source_record_id) DO UPDATE SET" not in sql
    assert "lead_source_records_source_fingerprint_idx" in sql


def test_phase1_storage_preserves_quarantine_and_handoff() -> None:
    sql = _sql()
    assert "growth.lead_quarantine" in sql
    assert "growth.lead_phase1_handoffs" in sql
    assert "downstream_eligible boolean NOT NULL" in sql


def test_phase1_storage_is_rls_enabled() -> None:
    sql = _sql()
    for table in (
        "lead_source_records",
        "lead_processing_state",
        "lead_field_observations",
        "lead_validation_findings",
        "lead_duplicate_decisions",
        "lead_canonical_projection",
        "lead_quarantine",
        "lead_phase1_handoffs",
    ):
        assert f"ALTER TABLE growth.{table} ENABLE ROW LEVEL SECURITY;" in sql
