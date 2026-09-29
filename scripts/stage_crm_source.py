from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import psycopg

from sentinellayer_growth_engine.crm.migration import (
    build_staged_rows,
    load_source_rows,
    persist_staged_row,
    profile_source,
)
from sentinellayer_growth_engine.config import Settings
def _connection_factory() -> psycopg.Connection[Any]:
    settings = Settings(database_url=os.environ.get("SL_DATABASE_URL", ""))
    if not settings.database_url:
        raise RuntimeError("SL_DATABASE_URL is required for --apply")
    settings.assert_safe()
    return psycopg.connect(
        settings.database_url,
        connect_timeout=settings.database_connect_timeout_seconds,
        options=f"-c statement_timeout={settings.database_statement_timeout_seconds}",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage CRM migration rows with replay protection.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--snapshot-output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--importer-version", default="crm-mvp.v1")
    parser.add_argument("--apply", action="store_true", help="persist rows after profiling")
    args = parser.parse_args()

    try:
        snapshot = profile_source(
            source_name=args.name,
            path=args.source,
            importer_version=args.importer_version,
            limit=args.limit,
        )
        args.snapshot_output.write_text(
            json.dumps(snapshot.__dict__, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        _, rows = load_source_rows(args.source, limit=args.limit)
        staged = build_staged_rows(
            source_name=args.name,
            snapshot_hash=snapshot.file_sha256,
            rows=rows,
            importer_version=args.importer_version,
        )
        counts: dict[str, int] = {}
        for item in staged:
            counts[item.disposition] = counts.get(item.disposition, 0) + 1

        if args.apply:
            for item in staged:
                persist_staged_row(_connection_factory, item)
        print(json.dumps({
            "source_rows": len(staged),
            "dispositions": counts,
            "applied": bool(args.apply),
            "snapshot": str(args.snapshot_output),
        }, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, psycopg.Error) as exc:
        print(f"ERROR: CRM staging failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
