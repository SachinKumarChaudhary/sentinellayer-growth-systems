from __future__ import annotations

import argparse
import json
import os
import sys

import psycopg

from .config import Settings
from .db import Database
from .health import check as health_check


def _settings() -> Settings:
    return Settings(database_url=os.environ.get("SL_DATABASE_URL", ""))


def cmd_health(_: argparse.Namespace) -> int:
    return health_check()


def cmd_status(_: argparse.Namespace) -> int:
    settings = _settings()
    if not settings.database_url:
        print("ERROR: SL_DATABASE_URL is required", file=sys.stderr)
        return 2
    db = Database(settings.database_url)
    try:
        state = db.get_control_state()
    except (psycopg.Error, RuntimeError) as exc:
        print(f"ERROR: cannot read Operations control state: {exc}", file=sys.stderr)
        return 1
    output = {
        "environment": settings.environment,
        "real_email_enabled": settings.real_email_enabled,
        "worker_id": os.environ.get("SL_WORKER_ID"),
        "operations": state,
    }
    print(json.dumps(output, indent=2, default=str))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="slctl", description="SentinelLayer operator CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    health = subparsers.add_parser("health", help="run the non-consequential readiness check")
    health.set_defaults(func=cmd_health)

    status = subparsers.add_parser("status", help="show runtime and Operations control state")
    status.set_defaults(func=cmd_status)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(args.func(args))
