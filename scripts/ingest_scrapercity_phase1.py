from __future__ import annotations

import argparse
import csv
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psycopg

from sentinellayer_growth_engine.phase1 import ScraperCityAdapter, process_source_record
from sentinellayer_growth_engine.phase1.models import LeadSourceRecord
from sentinellayer_growth_engine.phase1.repository import Phase1Repository

SOURCE_NAME = "scrapercity"
SOURCE_VERSION = "Store Leads Shopify - US - ScraperCity.csv"
EXPECTED_COLUMNS = 42


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest ScraperCity leads through Phase 1.")
    parser.add_argument("--csv", type=Path, help="ScraperCity CSV input.")
    parser.add_argument("--limit", type=int, default=0, help="Process only the first N rows.")
    parser.add_argument("--dry-run", action="store_true", help="Process without database writes.")
    parser.add_argument(
        "--acquired-at",
        type=str,
        help="UTC acquisition timestamp. Defaults to the CSV file mtime.",
    )
    return parser.parse_args()


def _acquired_at(path: Path, value: str | None) -> datetime:
    if value:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("--acquired-at must include a timezone")
        return parsed.astimezone(UTC)
    return datetime.fromtimestamp(path.stat().st_mtime, UTC)


def _load_rows(path: Path, limit: int) -> list[tuple[int, dict[str, Any]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        if len(columns) != EXPECTED_COLUMNS:
            raise ValueError(
                f"expected {EXPECTED_COLUMNS} columns, found {len(columns)}"
            )
        rows: list[tuple[int, dict[str, Any]]] = []
        for row_number, row in enumerate(reader, start=1):
            rows.append((row_number, dict(row)))
            if limit and len(rows) >= limit:
                break
    return rows


def _records(rows: list[tuple[int, dict[str, Any]]], acquired_at: datetime) -> list[LeadSourceRecord]:
    adapter = ScraperCityAdapter()
    return [
        adapter.adapt(
            payload,
            acquired_at=acquired_at,
            source_record_key=str(row_number),
            source_version=SOURCE_VERSION,
        )
        for row_number, payload in rows
    ]


def _summarize(results: list[dict[str, Any]]) -> None:
    counts: dict[str, int] = {}
    for result in results:
        counts[result["state"]] = counts.get(result["state"], 0) + 1
    print(f"rows={len(results)}")
    for state in sorted(counts):
        print(f"{state}={counts[state]}")


def main() -> int:
    args = _parse_args()
    if not args.csv:
        raise SystemExit("--csv is required")

    rows = _load_rows(args.csv, args.limit)
    acquired_at = _acquired_at(args.csv, args.acquired_at)
    records = _records(rows, acquired_at)

    # Duplicate adjudication is intentionally performed against the complete
    # batch so exact duplicate payloads remain explainable before persistence.
    existing_records: list[LeadSourceRecord] = []
    if not args.dry_run:
        db_url = os.environ.get("SUPABASE_DB_URL")
        if not db_url:
            raise SystemExit("SUPABASE_DB_URL is required for live ingestion")
        with psycopg.connect(db_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT source_record_id, schema_version, source_name, source_version,
                           source_record_key, acquired_at, source_payload, mapped_fields,
                           raw_fingerprint, adapter_version
                    FROM growth.lead_source_records
                    ORDER BY received_at, source_record_id
                    """
                )
                existing_records = [
                    LeadSourceRecord.model_validate({
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
                    })
                    for row in cur.fetchall()
                ]

    results = [
        process_source_record(record, existing_records=[*existing_records, *records[:index]])
        for index, record in enumerate(records)
    ]

    if args.dry_run:
        _summarize(
            [
                {
                    "state": result.state,
                    "source_record_id": result.source_record.source_record_id,
                }
                for result in results
            ]
        )
        return 0

    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise SystemExit("SUPABASE_DB_URL is required for live ingestion")

    def connection_factory() -> psycopg.Connection[Any]:
        return psycopg.connect(db_url)

    repository = Phase1Repository(connection_factory)
    persisted = [
        repository.persist_result(result)
        for result in results
    ]

    _summarize(persisted)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
