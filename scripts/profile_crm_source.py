from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sentinellayer_growth_engine.crm.migration import profile_source


def main() -> int:
    parser = argparse.ArgumentParser(description="Profile a CRM migration source without mutating Supabase.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--importer-version", default="crm-mvp.v1")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    try:
        snapshot = profile_source(
            source_name=args.name,
            path=args.source,
            importer_version=args.importer_version,
            limit=args.limit,
        )
        payload = json.dumps(snapshot.__dict__, indent=2, default=str)
        if args.output:
            args.output.write_text(payload + "\n", encoding="utf-8")
        else:
            print(payload)
        return 0
    except (OSError, ValueError) as exc:
        print(f"ERROR: CRM source profiling failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
#
# Stage only after reviewing the generated snapshot. This companion command is
# intentionally separate from profiling so the source contract cannot be skipped.
