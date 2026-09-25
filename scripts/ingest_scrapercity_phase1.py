from __future__ import annotations

import argparse
import csv
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg

from sentinellayer_growth_engine.config import Settings
from sentinellayer_growth_engine.phase1 import ScraperCityAdapter, process_source_record
from sentinellayer_growth_engine.phase1.models import LeadSourceRecord, Phase1Result
from sentinellayer_growth_engine.phase1.repository import Phase1Repository

SOURCE_NAME = "scrapercity"
SCRAPERCITY_SOURCE_FILE = "Store Leads Shopify - US - ScraperCity.csv"
EXPECTED_COLUMNS = 42


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest ScraperCity rows through the durable Phase 1 pipeline."
    )
    parser.add_argument("--csv", type=Path, help="ScraperCity CSV input.")
    parser.add_argument(
        "--from-legacy-db",
        action="store_true",
        help="Read the preserved ScraperCity observations from growth.company_source_data.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Process only the first N rows.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process and reconcile without writing to Supabase.",
    )
    parser.add_argument(
        "--acquired-at",
        type=str,
        help="UTC acquisition timestamp for CSV mode. Defaults to the CSV file mtime.",
    )
    return parser.parse_args()


def _settings() -> Settings:
    settings = Settings()
    settings.assert_safe()
    if not settings.database_url:
        raise RuntimeError("SL_DATABASE_URL is required for database mode")
    return settings


def _connection_factory() -> psycopg.Connection[Any]:
    settings = _settings()
    return psycopg.connect(
        settings.database_url,
        connect_timeout=settings.database_connect_timeout_seconds,
        options=f"-c statement_timeout={settings.database_statement_timeout_seconds}",
    )


def _acquired_at(path: Path, value: str | None) -> datetime:
    if value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("--acquired-at must include a timezone")
        return parsed.astimezone(UTC)
    return datetime.fromtimestamp(path.stat().st_mtime, UTC)


def _load_csv_rows(
    path: Path, limit: int
) -> list[tuple[int, dict[str, Any], datetime, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        if len(columns) != EXPECTED_COLUMNS:
            raise ValueError(
                f"expected {EXPECTED_COLUMNS} columns, found {len(columns)}"
            )

        rows: list[tuple[int, dict[str, Any], datetime, str]] = []
        acquired_at = _acquired_at(path, None)
        for row_number, row in enumerate(reader, start=1):
            rows.append((row_number, dict(row), acquired_at, path.name))
            if limit and len(rows) >= limit:
                break

    if not rows:
        raise ValueError("ScraperCity CSV contains no data rows")
    return rows


def _load_legacy_rows(
    limit: int,
) -> list[tuple[int, dict[str, Any], datetime, str]]:
    with _connection_factory() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT source_row_number, raw_row_json, imported_at, source_file
            FROM growth.company_source_data
            WHERE source_file = %s
            ORDER BY source_row_number
            """,
            (SCRAPERCITY_SOURCE_FILE,),
        )
        raw_rows = cur.fetchall()

    rows: list[tuple[int, dict[str, Any], datetime, str]] = []
    for source_row_number, raw_payload, imported_at, source_file in raw_rows:
        if not isinstance(raw_payload, dict) or not raw_payload:
            raise ValueError(
                f"invalid raw_row_json at source row {source_row_number}"
            )
        acquired_at = (
            imported_at.astimezone(UTC)
            if imported_at.tzinfo
            else imported_at.replace(tzinfo=UTC)
        )
        rows.append(
            (int(source_row_number), raw_payload, acquired_at, str(source_file))
        )
        if limit and len(rows) >= limit:
            break

    if not rows:
        raise ValueError(
            "no ScraperCity observations found in growth.company_source_data"
        )
    return rows


def _records(
    rows: list[tuple[int, dict[str, Any], datetime, str]],
) -> list[LeadSourceRecord]:
    adapter = ScraperCityAdapter()
    return [
        adapter.adapt(
            payload,
            acquired_at=acquired_at,
            source_record_key=str(row_number),
            source_version=source_version,
        )
        for row_number, payload, acquired_at, source_version in rows
    ]


def prepare_results(
    rows: list[tuple[int, dict[str, Any], datetime, str]],
    *,
    existing_records: list[LeadSourceRecord] | None = None,
) -> list[Phase1Result]:
    records = _records(rows)
    prior = list(existing_records or [])
    results: list[Phase1Result] = []

    for index, record in enumerate(records):
        result = process_source_record(
            record,
            existing_records=[*prior, *records[:index]],
            now=record.acquired_at,
        )
        results.append(result)

    return results


def main() -> int:
    args = _parse_args()
    try:
        if args.from_legacy_db:
            rows = _load_legacy_rows(args.limit)
        else:
            if not args.csv:
                raise ValueError("--csv is required unless --from-legacy-db is used")
            rows = _load_csv_rows(args.csv, args.limit)

        if args.dry_run:
            results = prepare_results(rows)
        else:
            repository = Phase1Repository(_connection_factory)
            existing_records = repository.load_source_records(SOURCE_NAME)
            results = prepare_results(
                rows,
                existing_records=existing_records,
            )

            persisted = 0
            for result in results:
                repository.persist_result(result)
                persisted += 1

            print(f"rows={len(rows)}")
            print(f"persisted={persisted}")
            return 0

        state_counts: dict[str, int] = {}
        duplicate_counts: dict[str, int] = {}
        for result in results:
            state_counts[result.state] = state_counts.get(result.state, 0) + 1
            duplicate_type = result.duplicate_decision.duplicate_type
            duplicate_counts[duplicate_type] = (
                duplicate_counts.get(duplicate_type, 0) + 1
            )

        print(f"rows={len(results)}")
        for state in sorted(state_counts):
            print(f"{state}={state_counts[state]}")
        for duplicate_type in sorted(duplicate_counts):
            print(f"duplicate_{duplicate_type}={duplicate_counts[duplicate_type]}")
        return 0

    except (OSError, RuntimeError, ValueError, psycopg.Error) as exc:
        print(f"ERROR: ScraperCity Phase 1 ingestion failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
