from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sentinellayer_growth_engine.crm.migration import (
    build_operational_sheet_staged_rows,
    load_source_rows,
    operational_sheet_profile,
    profile_source,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run the operational CRM Sheet migration.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--name", default="sentinellayer-outreach-sheet")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        snapshot = profile_source(
            source_name=args.name,
            path=args.source,
            importer_version="crm-mvp.sheet.v1",
        )
        _, rows = load_source_rows(args.source)
        staged = build_operational_sheet_staged_rows(
            source_name=args.name,
            snapshot_hash=snapshot.file_sha256,
            rows=rows,
            importer_version="crm-mvp.sheet.v1",
        )
        profile = operational_sheet_profile(staged)
        report = {
            "source": {
                "name": snapshot.source_name,
                "sha256": snapshot.file_sha256,
                "row_count": snapshot.row_count,
                "headers": snapshot.headers,
                "null_rates": snapshot.null_rates,
            },
            "migration_profile": profile,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: dry-run failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
