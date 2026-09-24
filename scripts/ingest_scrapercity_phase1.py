from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg

from sentinellayer_growth_engine.config import Settings
from sentinellayer_growth_engine.phase1 import ScraperCityAdapter, process_source_record
from sentinellayer_growth_engine.phase1.models import LeadSourceRecord
from sentinellayer_growth_engine.phase1.repository import Phase1Repository

SOURCE_NAME = "scrapercity"
EXPECTED_COLUMNS = 42


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest ScraperCity rows through the durable Phase 1 pipeline."
    )
    parser.add_argument("--csv", type=Path, required=True, help="ScraperCity CSV input.")
    parser.add_argument("--limit", type=int, default=0, help="Process only the first N rows.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Process and reconcile without writing to Supabase.",
    )
    parser.add_argument(
        "--acquired-at",
        type=str,
        help="UTC acquisition timestamp. Defaults to the CSV file mtime.",
    )
    return parser.parse_args()


def _connection_factory() -> psycopg.Connection[Any]:
    settings = Settings()
    settings.assert_safe()
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


def _load_rows(path: Path, limit: int) -> list[tuple[int, dict[str, Any]]]:
    import csv

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        if len(columns) != EXPECTED_COLUMNS:
            raise ValueError(
                f"expected {EXPECTED_COLUMNS} columns, found {len(columns)}"
            )

        rows: list[tuple[int, dict[str, Any]]] = []
        for row_number, row in enumerate(reader, start=1):
            rows.append((row_number, {key: value for key, value in row.items()}))
            if limit and len(rows) >= limit:
                break

    if not rows:
        raise ValueError("ScraperCity CSV contains no data rows")
    return rows


def _records(
    rows: list[tuple[int, dict[str, Any]]],
    acquired_at: datetime,
    source_version: str,
) -> list[LeadSourceRecord]:
    adapter = ScraperCityAdapter()
    return [
        adapter.adapt(
            payload,
            acquired_at=acquired_at,
            source_record_key=str(row_number),
            source_version=source_version,
        )
        for row_number, payload in rows
    ]


def prepare_results(
    rows: list[tuple[int, dict[str, Any]]],
    *,
    acquired_at: datetime,
    source_version: str,
    existing_records: list[LeadSourceRecord] | None = None,
) -> list[Any]:
    records = _records(rows, acquired_at, source_version)
    prior = list(existing_records or [])
    results = []

    for index, record in enumerate(records):
        result = process_source_record(
            record,
            existing_records=[*prior, *records[:index]],
            now=acquired_at,
        )
        results.append(result)

    return results


def main() -> int:
    args = _parse_args()
    try:
        acquired_at = _acquired_at(args.csv, args.acquired_at)
        rows = _load_rows(args.csv, args.limit)
        results = prepare_results(
            rows,
            acquired_at=acquired_at,
            source_version=args.csv.name,
        )

        if args.dry_run:
            for result in results:
                print(
                    result.source_record.source_record_id,
                    result.state,
                    result.duplicate_decision.duplicate_type,
                )
            return 0

        repository = Phase1Repository(_connection_factory)
        existing_records = repository.load_source_records(SOURCE_NAME)
        results = prepare_results(
            rows,
            acquired_at=acquired_at,
            source_version=args.csv.name,
            existing_records=existing_records,
        )

        persisted = 0
        for result in results:
            repository.persist_result(result)
            persisted += 1

        print(f"rows={len(rows)}")
        print(f"persisted={persisted}")
        return 0
    except (OSError, RuntimeError, ValueError, psycopg.Error) as exc:
        print(f"ERROR: ScraperCity Phase 1 ingestion failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
