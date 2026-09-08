from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg

from .config import Settings
from .db import Database
from .enrichment_contracts import EnrichmentBatch
from .enrichment_repository import EnrichmentRepository
from .health import check as health_check
from .tinyfish_client import TinyFishClient, TinyFishError


def _settings() -> Settings:
    return Settings(database_url=os.environ.get("SL_DATABASE_URL", ""))


def _connection_factory() -> psycopg.Connection[object]:
    settings = _settings()
    if not settings.database_url:
        raise RuntimeError("SL_DATABASE_URL is required")
    return psycopg.connect(settings.database_url)


def _tinyfish_client() -> TinyFishClient:
    settings = _settings()
    if not settings.tinyfish_api_key:
        raise RuntimeError("SL_TINYFISH_API_KEY is required")
    return TinyFishClient(
        settings.tinyfish_api_key,
        search_url=settings.tinyfish_search_url,
        fetch_url=settings.tinyfish_fetch_url,
        timeout_seconds=settings.tinyfish_timeout_seconds,
    )


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


def cmd_enrichment_export(args: argparse.Namespace) -> int:
    repository = EnrichmentRepository(_connection_factory)
    rows = repository.next_companies(limit=args.limit)
    print(json.dumps({"schema_version": "1.0", "companies": rows}, indent=2, default=str))
    return 0


def cmd_enrichment_import(args: argparse.Namespace) -> int:
    try:
        payload = json.loads(Path(args.file).read_text(encoding="utf-8"))
        batch = EnrichmentBatch.model_validate(payload)
        repository = EnrichmentRepository(_connection_factory)
        result = repository.persist_batch(batch, provider=args.provider)
    except (OSError, ValueError, json.JSONDecodeError, psycopg.Error, RuntimeError) as exc:
        print(f"ERROR: enrichment import failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, default=str))
    return 0


def cmd_tinyfish_search(args: argparse.Namespace) -> int:
    try:
        client = _tinyfish_client()
        results = client.search(args.query, purpose=args.purpose)
    except (RuntimeError, TinyFishError, ValueError) as exc:
        print(f"ERROR: TinyFish search failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps([result.__dict__ for result in results], indent=2))
    return 0


def cmd_tinyfish_fetch(args: argparse.Namespace) -> int:
    try:
        client = _tinyfish_client()
        results = client.fetch(args.url, purpose=args.purpose)
    except (RuntimeError, TinyFishError, ValueError) as exc:
        print(f"ERROR: TinyFish fetch failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps([result.__dict__ for result in results], indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="slctl", description="SentinelLayer operator CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    health = subparsers.add_parser("health", help="run the non-consequential readiness check")
    health.set_defaults(func=cmd_health)

    status = subparsers.add_parser("status", help="show runtime and Operations control state")
    status.set_defaults(func=cmd_status)

    enrichment = subparsers.add_parser("enrichment", help="operator-assisted company enrichment")
    enrichment_sub = enrichment.add_subparsers(dest="enrichment_command", required=True)

    export_cmd = enrichment_sub.add_parser("export-next", help="print the next un-enriched 1-3 companies")
    export_cmd.add_argument("--limit", type=int, default=3, choices=range(1, 4))
    export_cmd.set_defaults(func=cmd_enrichment_export)

    import_cmd = enrichment_sub.add_parser("import", help="persist a validated AI enrichment batch JSON")
    import_cmd.add_argument("--file", required=True)
    import_cmd.add_argument("--provider", default="manual_ai_research")
    import_cmd.set_defaults(func=cmd_enrichment_import)

    tinyfish = subparsers.add_parser(
        "tinyfish", help="read-only TinyFish Search and Fetch access for research"
    )
    tinyfish_sub = tinyfish.add_subparsers(dest="tinyfish_command", required=True)

    search_cmd = tinyfish_sub.add_parser("search", help="search the public web with TinyFish")
    search_cmd.add_argument("query")
    search_cmd.add_argument("--purpose")
    search_cmd.set_defaults(func=cmd_tinyfish_search)

    fetch_cmd = tinyfish_sub.add_parser("fetch", help="fetch up to ten known URLs with TinyFish")
    fetch_cmd.add_argument("url", nargs="+", metavar="URL")
    fetch_cmd.add_argument("--purpose")
    fetch_cmd.set_defaults(func=cmd_tinyfish_fetch)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(args.func(args))
