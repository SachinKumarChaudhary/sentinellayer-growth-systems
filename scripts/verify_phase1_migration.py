from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg


REQUIRED_TABLES = (
    "lead_source_records",
    "lead_processing_state",
    "lead_field_observations",
    "lead_validation_findings",
    "lead_duplicate_decisions",
    "lead_canonical_projection",
    "lead_quarantine",
    "lead_phase1_handoffs",
)


def verify(database_url: str, migration_path: Path) -> None:
    migration = migration_path.read_text(encoding="utf-8")
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("BEGIN")
            cur.execute(migration)
            cur.execute(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'growth'
                  AND tablename = ANY(%s)
                """,
                (list(REQUIRED_TABLES),),
            )
            tables = {row[0] for row in cur.fetchall()}
            missing = set(REQUIRED_TABLES) - tables
            if missing:
                raise RuntimeError(f"missing Phase 1 tables: {sorted(missing)}")

            cur.execute(
                """
                SELECT count(*)
                FROM pg_indexes
                WHERE schemaname = 'growth'
                  AND indexname = 'lead_source_records_source_fingerprint_idx'
                """
            )
            if cur.fetchone()[0] != 1:
                raise RuntimeError("source fingerprint index missing")

            cur.execute(
                """
                SELECT count(*)
                FROM pg_trigger
                WHERE tgname IN (
                    'lead_source_records_immutable',
                    'lead_field_observations_immutable',
                    'lead_validation_findings_immutable',
                    'lead_duplicate_decisions_immutable'
                )
                """
            )
            if cur.fetchone()[0] != 4:
                raise RuntimeError("Phase 1 immutability triggers missing")

            cur.execute(
                """
                INSERT INTO growth.lead_source_records
                    (source_record_id, schema_version, source_name, acquired_at,
                     source_payload, mapped_fields, raw_fingerprint, adapter_version)
                VALUES
                    ('migration-test', 'v1', 'migration_test', now(),
                     '{"domain":"example.com"}'::jsonb, '[]'::jsonb,
                     repeat('a', 64), 'migration-test.v1')
                """
            )

            cur.execute(
                """
                SELECT count(*)
                FROM growth.lead_source_records
                WHERE source_record_id = 'migration-test'
                """
            )
            if cur.fetchone()[0] != 1:
                raise RuntimeError("synthetic insert failed")

            cur.execute("ROLLBACK")
    print("PHASE1_MIGRATION_VERIFY_PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database-url",
        default=os.getenv("SUPABASE_DB_URL") or os.getenv("DATABASE_URL"),
    )
    parser.add_argument(
        "--migration",
        type=Path,
        default=Path("supabase/migrations/20260924010000_phase1_lead_intake_storage.sql"),
    )
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("SUPABASE_DB_URL or DATABASE_URL is required")
    verify(args.database_url, args.migration)


if __name__ == "__main__":
    main()
