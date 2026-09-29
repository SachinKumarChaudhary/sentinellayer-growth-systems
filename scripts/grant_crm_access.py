from __future__ import annotations

import argparse
import os
import sys
from uuid import UUID

import psycopg

from sentinellayer_growth_engine.config import Settings


def main() -> int:
    parser = argparse.ArgumentParser(description="Grant a Supabase Auth user CRM access.")
    parser.add_argument("--user-id", required=True, type=UUID)
    parser.add_argument("--role", choices=["OPERATOR", "REVIEWER", "ADMIN"], default="OPERATOR")
    args = parser.parse_args()
    try:
        settings = Settings(database_url=os.environ.get("SL_DATABASE_URL", ""))
        if not settings.database_url:
            raise RuntimeError("SL_DATABASE_URL is required")
        settings.assert_safe()
        with psycopg.connect(settings.database_url) as conn, conn.cursor() as cur:
            cur.execute("select id from auth.users where id = %s", (args.user_id,))
            if cur.fetchone() is None:
                raise RuntimeError("Supabase Auth user does not exist")
            cur.execute(
                """
                insert into crm.user_access(user_id,role,active)
                values (%s,%s,true)
                on conflict (user_id)
                do update set role=excluded.role, active=true, updated_at=now()
                returning user_id, role, active
                """,
                (args.user_id, args.role),
            )
            print(cur.fetchone())
        return 0
    except (OSError, ValueError, RuntimeError, psycopg.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
