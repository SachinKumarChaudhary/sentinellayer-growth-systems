from sentinellayer_growth_engine.tinyfish_rate_limit import (
    TinyFishQuotaExceeded,
    TinyFishRateLimitPolicy,
    TinyFishRateLimiter,
)


def test_search_minute_budget_has_conservative_headroom() -> None:
    limiter = TinyFishRateLimiter(
        TinyFishRateLimitPolicy(
            search_per_minute=2,
            search_per_hour=10,
            fetch_urls_per_minute=10,
            fetch_urls_per_day=100,
        )
    )

    limiter.acquire_search()
    limiter.acquire_search()

    try:
        limiter.acquire_search()
    except TinyFishQuotaExceeded as exc:
        assert "minute budget exhausted" in str(exc)
    else:
        raise AssertionError("expected Search minute quota failure")


def test_search_hour_budget_is_independent() -> None:
    limiter = TinyFishRateLimiter(
        TinyFishRateLimitPolicy(
            search_per_minute=10,
            search_per_hour=2,
            fetch_urls_per_minute=10,
            fetch_urls_per_day=100,
        )
    )

    limiter.acquire_search()
    limiter.acquire_search()

    try:
        limiter.acquire_search()
    except TinyFishQuotaExceeded as exc:
        assert "hourly safety budget exhausted" in str(exc)
    else:
        raise AssertionError("expected Search hourly quota failure")


def test_fetch_budget_is_counted_by_urls_not_requests() -> None:
    limiter = TinyFishRateLimiter(
        TinyFishRateLimitPolicy(
            search_per_minute=10,
            search_per_hour=100,
            fetch_urls_per_minute=5,
            fetch_urls_per_day=20,
        )
    )

    limiter.acquire_fetch(3)

    try:
        limiter.acquire_fetch(3)
    except TinyFishQuotaExceeded as exc:
        assert "Fetch minute budget exhausted" in str(exc)
    else:
        raise AssertionError("expected Fetch minute quota failure")


def test_fetch_daily_budget_is_hard_capped() -> None:
    limiter = TinyFishRateLimiter(
        TinyFishRateLimitPolicy(
            search_per_minute=10,
            search_per_hour=100,
            fetch_urls_per_minute=100,
            fetch_urls_per_day=5,
        )
    )

    limiter.acquire_fetch(5)

    try:
        limiter.acquire_fetch(1)
    except TinyFishQuotaExceeded as exc:
        assert "daily safety budget exhausted" in str(exc)
    else:
        raise AssertionError("expected Fetch daily quota failure")
