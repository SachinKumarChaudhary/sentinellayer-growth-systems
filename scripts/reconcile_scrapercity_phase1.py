from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


from sentinellayer_growth_engine.phase1 import ScraperCityAdapter, process_source_record


def _payload(row: dict[str, Any]) -> dict[str, Any]:
    return {key: (value if value not in ('', None) else None) for key, value in row.items()}


def reconcile(path: Path, expected_rows: int | None = None) -> dict[str, Any]:
    with path.open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        rows = list(reader)
    if expected_rows is not None and len(rows) != expected_rows:
        raise ValueError(f"expected {expected_rows} rows, found {len(rows)}")

    acquired_at = datetime.now(UTC)
    adapter = ScraperCityAdapter()
    states: Counter[str] = Counter()
    findings: Counter[str] = Counter()
    domains: defaultdict[str, list[int]] = defaultdict(list)
    records: list[Any] = []

    for row_number, row in enumerate(rows):
        record = adapter.adapt(
            _payload(row),
            acquired_at=acquired_at,
            source_record_key=str(row_number),
        )
        result = process_source_record(
            record,
            existing_records=records,
            now=acquired_at,
        )
        records.append(record)
        states[result.state] += 1
        for finding in result.findings:
            findings[finding.code] += 1
        if result.canonical_lead and result.canonical_lead.domain:
            domains[result.canonical_lead.domain].append(int(row_number))

    duplicate_domains = {
        domain: rows for domain, rows in domains.items() if len(rows) > 1
    }
    return {
        "source": "scrapercity",
        "path": str(path),
        "row_count": len(rows),
        "column_count": len(columns),
        "columns": columns,
        "states": dict(states),
        "finding_counts": dict(findings),
        "normalized_domain_count": len(domains),
        "duplicate_normalized_domain_count": len(duplicate_domains),
        "duplicate_normalized_domains": duplicate_domains,
        "phase2_required_for_entity_review": bool(duplicate_domains),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Dry-run ScraperCity through Phase 1.")
    parser.add_argument("csv", type=Path)
    parser.add_argument("--expected-rows", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = reconcile(args.csv, args.expected_rows)
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
