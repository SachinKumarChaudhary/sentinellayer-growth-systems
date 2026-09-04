from __future__ import annotations

import os
import socket
import sys

import psycopg

from .config import Settings


def check() -> int:
    """Non-consequential liveness/readiness check for container runtimes."""
    try:
        os.kill(1, 0)
        dsn = os.environ.get("SL_DATABASE_URL", "")
        if not dsn:
            print("NOT_READY: SL_DATABASE_URL is missing")
            return 1
        settings = Settings(database_url=dsn)
        settings.assert_safe()
        with psycopg.connect(dsn, connect_timeout=3) as conn, conn.cursor() as cur:
                cur.execute("select 1")
                if cur.fetchone() != (1,):
                    print("NOT_READY: database probe returned an unexpected result")
                    return 1
        print(f"READY: host={socket.gethostname()} environment={settings.environment}")
        return 0
    except (OSError, psycopg.Error, ValueError):
        print("NOT_READY: readiness check failed")
        return 1


if __name__ == "__main__":
    sys.exit(check())
