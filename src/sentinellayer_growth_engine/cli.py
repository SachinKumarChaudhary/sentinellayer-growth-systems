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
from .tinyfish_batch import (
    DatabaseCompanySeedResolver,
    TinyFishBatchEnricher,
    TinyFishDailyEnricher,
    TinyFishRefreshEnricher,
)
from .tinyfish_client import TinyFishClient
from .tinyfish_rate_limit import TinyFishRateLimitPolicy, TinyFishRateLimiter
from .tinyfish_enrichment import TinyFishEnrichmentProvider


def _settings() -> Settings:
    return Settings(database_url=os.environ.get("SL_DATABASE_URL", ""))


def _connection_factory() -> psycopg.Connection[object]:
    settings = _settings()
    if not settings.database_url:
        raise RuntimeError("SL_DATABASE_URL is required")
    return psycopg.connect(settings.database_url)


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


def _tinyfish_client(settings: Settings) -> TinyFishClient:
    if not settings.tinyfish_api_key:
        raise RuntimeError("SL_TINYFISH_API_KEY is required")
    limiter = TinyFishRateLimiter(
        TinyFishRateLimitPolicy(
            search_per_minute=settings.tinyfish_search_per_minute,
            search_per_hour=settings.tinyfish_search_per_hour,
            fetch_urls_per_minute=settings.tinyfish_fetch_urls_per_minute,
            fetch_urls_per_day=settings.tinyfish_fetch_urls_per_day,
            max_retry_attempts=settings.tinyfish_max_retry_attempts,
        )
    )
    return TinyFishClient(
        settings.tinyfish_api_key,
        search_url=settings.tinyfish_search_url,
        fetch_url=settings.tinyfish_fetch_url,
        timeout_seconds=settings.tinyfish_timeout_seconds,
        rate_limiter=limiter,
        max_retry_attempts=settings.tinyfish_max_retry_attempts,
    )


def cmd_enrichment_research(args: argparse.Namespace) -> int:
    try:
        settings = _settings()
        provider = TinyFishEnrichmentProvider(_tinyfish_client(settings))
        packet = provider.build_packet(
            company_id=args.company_id,
            domain=args.domain,
            merchant_name=args.merchant_name,
        )
        print(json.dumps(packet.model_dump(mode="json"), indent=2, default=str))
        return 0
    except (ValueError, RuntimeError) as exc:
        print(f"ERROR: TinyFish enrichment failed: {exc}", file=sys.stderr)
        return 1


def cmd_enrichment_tinyfish_next(args: argparse.Namespace) -> int:
    try:
        settings = _settings()
        repository = EnrichmentRepository(_connection_factory)
        provider = TinyFishEnrichmentProvider(_tinyfish_client(settings))
        enricher = TinyFishBatchEnricher(
            repository=repository,
            provider=provider,
            seed_resolver=DatabaseCompanySeedResolver(_connection_factory),
        )
        result = enricher.run_next(limit=args.limit, persist=not args.dry_run)
        print(json.dumps(result, indent=2, default=str))
        return 0
    except (ValueError, RuntimeError, psycopg.Error) as exc:
        print(f"ERROR: TinyFish next-batch enrichment failed: {exc}", file=sys.stderr)
        return 1


def cmd_enrichment_tinyfish_daily(args: argparse.Namespace) -> int:
    try:
        settings = _settings()
        repository = EnrichmentRepository(_connection_factory)
        provider = TinyFishEnrichmentProvider(_tinyfish_client(settings))
        result = TinyFishDailyEnricher(
            repository=repository,
            provider=provider,
            seed_resolver=DatabaseCompanySeedResolver(_connection_factory),
        ).run_daily(limit=args.limit)
        print(json.dumps(result.__dict__, indent=2, default=str))
        return 0 if result.failed == 0 else 1
    except (ValueError, RuntimeError, psycopg.Error) as exc:
        print(f"ERROR: TinyFish daily enrichment failed: {exc}", file=sys.stderr)
        return 1


def cmd_enrichment_tinyfish_refresh(args: argparse.Namespace) -> int:
    try:
        settings = _settings()
        repository = EnrichmentRepository(_connection_factory)
        provider = TinyFishEnrichmentProvider(_tinyfish_client(settings))
        result = TinyFishRefreshEnricher(
            repository=repository,
            provider=provider,
            seed_resolver=DatabaseCompanySeedResolver(_connection_factory),
        ).run_refresh(limit=args.limit, min_age_days=args.min_age_days)
        print(json.dumps(result.__dict__, indent=2, default=str))
        return 0 if result.failed == 0 else 1
    except (ValueError, RuntimeError, psycopg.Error) as exc:
        print(f"ERROR: TinyFish refresh enrichment failed: {exc}", file=sys.stderr)
        return 1


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

    research_cmd = enrichment_sub.add_parser(
        "tinyfish",
        help="build one conservative EnrichmentPacket from TinyFish public evidence",
    )
    research_cmd.add_argument("--company-id", type=int, required=True)
    research_cmd.add_argument("--domain", required=True)
    research_cmd.add_argument("--merchant-name")
    research_cmd.set_defaults(func=cmd_enrichment_research)

    batch_cmd = enrichment_sub.add_parser(
        "tinyfish-next",
        help="enrich and persist the next 1-3 companies from TinyFish public evidence",
    )
    batch_cmd.add_argument("--limit", type=int, default=3, choices=range(1, 4))
    batch_cmd.add_argument("--dry-run", action="store_true", help="build the batch without persisting it")
    batch_cmd.set_defaults(func=cmd_enrichment_tinyfish_next)

    daily_cmd = enrichment_sub.add_parser(
        "tinyfish-daily",
        help="enrich up to 40 new companies using TinyFish and persist each company independently",
    )
    daily_cmd.add_argument("--limit", type=int, default=40, choices=range(1, 41))
    daily_cmd.set_defaults(func=cmd_enrichment_tinyfish_daily)

    refresh_cmd = enrichment_sub.add_parser(
        "tinyfish-refresh",
        help="refresh up to 20 stale enriched companies, prioritizing higher-priority accounts",
    )
    refresh_cmd.add_argument("--limit", type=int, default=10, choices=range(1, 21))
    refresh_cmd.add_argument("--min-age-days", type=int, default=7, choices=range(1, 31))
    refresh_cmd.set_defaults(func=cmd_enrichment_tinyfish_refresh)

    import_cmd = enrichment_sub.add_parser("import", help="persist a validated enrichment batch JSON")
    import_cmd.add_argument("--file", required=True)
    import_cmd.add_argument("--provider", default="manual_ai_research")
    import_cmd.set_defaults(func=cmd_enrichment_import)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    raise SystemExit(args.func(args))
