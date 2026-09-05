"""Apply repository Supabase migrations to the isolated integration database.

The integration workflow must validate the schema and functions that the tests
exercise. This script is intentionally deterministic and fail-closed: any
migration error aborts the job. Production databases are never targeted by CI.
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "supabase" / "migrations"


def main() -> None:
    dsn = os.environ.get("SUPABASE_DATABASE_URL")
    if not dsn:
        raise SystemExit("SUPABASE_DATABASE_URL is required")

    files = sorted(MIGRATIONS.glob("*.sql"))
    if not files:
        raise SystemExit("no Supabase migrations found")

    with psycopg.connect(dsn, autocommit=True) as conn:
        for path in files:
            print(f"Applying migration: {path.name}")
            sql = path.read_text(encoding="utf-8")
            with conn.cursor() as cur:
                cur.execute(sql)

    print(f"Applied {len(files)} migration files.")


if __name__ == "__main__":
    main()
