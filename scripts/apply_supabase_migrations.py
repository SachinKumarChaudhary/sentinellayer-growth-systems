"""Apply repository Supabase migrations to the isolated integration database.

CI runs against a persistent Supabase integration database. Migrations are
tracked by a repository-local table so already-applied migrations are skipped
without swallowing genuine SQL errors.
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
        with conn.cursor() as cur:
            cur.execute(
                """
                create table if not exists public._ci_migration_history (
                    filename text primary key,
                    applied_at timestamptz not null default now()
                )
                """
            )

        for path in files:
            with conn.cursor() as cur:
                cur.execute(
                    "select 1 from public._ci_migration_history where filename = %s",
                    (path.name,),
                )
                if cur.fetchone():
                    print(f"Skipping applied migration: {path.name}")
                    continue

                print(f"Applying migration: {path.name}")
                cur.execute(path.read_text(encoding="utf-8"))
                cur.execute(
                    "insert into public._ci_migration_history(filename) values (%s)",
                    (path.name,),
                )

    print(f"Processed {len(files)} migration files.")


if __name__ == "__main__":
    main()
