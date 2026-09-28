from __future__ import annotations

import argparse
import os
import sys
from typing import Any

import psycopg

from sentinellayer_growth_engine.config import Settings
from sentinellayer_growth_engine.phase2.execution import Phase2BatchExecutor
from sentinellayer_growth_engine.phase2.extraction import GroqEntityEvidenceExtractor
from sentinellayer_growth_engine.phase2.repository import Phase2Repository
from sentinellayer_growth_engine.phase2.research import TinyFishResearchAdapter
from sentinellayer_growth_engine.phase2.tinyfish_provider import (
    TinyFishEntityCandidateProvider,
    TinyFishTelemetryBuffer,
)
from sentinellayer_growth_engine.phase1.repository import Phase1Repository
from sentinellayer_growth_engine.tinyfish_client import TinyFishClient
from sentinellayer_growth_engine.tinyfish_rate_limit import (
    TinyFishRateLimitPolicy,
    TinyFishRateLimiter,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a bounded Phase 2 entity-resolution batch against eligible Phase 1 handoffs."
    )
    parser.add_argument(
        "--request-key",
        required=True,
        help="Stable idempotency key for this Phase 2 run.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of eligible Phase 1 handoffs to process. Defaults to 10.",
    )
    parser.add_argument(
        "--candidate-budget",
        type=int,
        default=25,
        help="Maximum Phase 2 candidates considered per lead.",
    )
    parser.add_argument(
        "--max-search-results",
        type=int,
        default=5,
        help="Maximum TinyFish Search results retained per lead.",
    )
    parser.add_argument(
        "--max-fetch-urls",
        type=int,
        default=3,
        help="Maximum TinyFish Fetch URLs inspected per lead.",
    )
    parser.add_argument(
        "--no-groq",
        action="store_true",
        help="Disable optional Groq semantic extraction and use deterministic extraction only.",
    )
    parser.add_argument(
        "--groq-model",
        default=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
        help="Groq model for bounded semantic evidence extraction.",
    )
    return parser.parse_args()


def _settings() -> Settings:
    database_url = os.getenv("SL_DATABASE_URL") or os.getenv("SUPABASE_DATABASE_URL")
    if not database_url:
        raise RuntimeError("SL_DATABASE_URL or SUPABASE_DATABASE_URL is required")
    os.environ["SL_DATABASE_URL"] = database_url

    settings = Settings()
    settings.assert_safe()
    if not settings.tinyfish_api_key and not os.getenv("TINYFISH_API_KEY"):
        raise RuntimeError("SL_TINYFISH_API_KEY or TINYFISH_API_KEY is required")
    return settings


def _connection_factory(settings: Settings) -> psycopg.Connection[Any]:
    return psycopg.connect(
        settings.database_url,
        connect_timeout=settings.database_connect_timeout_seconds,
        options=f"-c statement_timeout={settings.database_statement_timeout_seconds}",
    )


def main() -> int:
    args = _parse_args()
    try:
        if args.limit < 1:
            raise ValueError("--limit must be positive")
        if args.candidate_budget < 1:
            raise ValueError("--candidate-budget must be positive")
        if args.max_search_results < 1:
            raise ValueError("--max-search-results must be positive")
        if not 1 <= args.max_fetch_urls <= 10:
            raise ValueError("--max-fetch-urls must be between 1 and 10")

        settings = _settings()
        tinyfish_api_key = settings.tinyfish_api_key or os.environ["TINYFISH_API_KEY"]

        rate_limiter = TinyFishRateLimiter(
            TinyFishRateLimitPolicy(
                search_per_minute=settings.tinyfish_search_per_minute,
                search_per_hour=settings.tinyfish_search_per_hour,
                fetch_urls_per_minute=settings.tinyfish_fetch_urls_per_minute,
                fetch_urls_per_day=settings.tinyfish_fetch_urls_per_day,
                max_retry_attempts=settings.tinyfish_max_retry_attempts,
            )
        )
        telemetry = TinyFishTelemetryBuffer()
        client = TinyFishClient(
            tinyfish_api_key,
            search_url=settings.tinyfish_search_url,
            fetch_url=settings.tinyfish_fetch_url,
            timeout_seconds=settings.tinyfish_timeout_seconds,
            rate_limiter=rate_limiter,
            max_retry_attempts=settings.tinyfish_max_retry_attempts,
            telemetry_sink=telemetry,
        )

        def connection_factory() -> psycopg.Connection[Any]:
            return _connection_factory(settings)

        phase1_repository = Phase1Repository(connection_factory)
        phase2_repository = Phase2Repository(connection_factory)

        groq_key = os.getenv("GROQ_API_KEY")
        groq_extractor = (
            GroqEntityEvidenceExtractor(
                api_key=groq_key,
                model=args.groq_model,
            )
            if groq_key and not args.no_groq
            else None
        )

        provider = TinyFishEntityCandidateProvider(
            TinyFishResearchAdapter(client),
            phase2_repository,
            telemetry,
            groq_extractor=groq_extractor,
            max_search_results=args.max_search_results,
            max_fetch_urls=args.max_fetch_urls,
        )
        result = Phase2BatchExecutor(
            phase1_repository,
            phase2_repository,
        ).run(
            request_key=args.request_key,
            candidate_provider=provider,
            limit=args.limit,
            candidate_budget=args.candidate_budget,
        )

        print(f"run_id={result.run_id}")
        print(f"request_key={result.request_key}")
        print(f"input_count={result.input_count}")
        print(f"decision_count={result.decision_count}")
        print(f"matched_count={result.matched_count}")
        print(f"research_required_count={result.research_required_count}")
        print(f"provider_error_count={result.provider_error_count}")
        print(f"groq_enabled={groq_extractor is not None}")
        return 0
    except (OSError, RuntimeError, ValueError, psycopg.Error) as exc:
        print(f"ERROR: Phase 2 batch failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
