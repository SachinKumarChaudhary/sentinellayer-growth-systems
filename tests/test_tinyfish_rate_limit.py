from sentinellayer_growth_engine.tinyfish_rate_limit import (
    TinyFishQuotaExceeded,
    TinyFishRateLimitPolicy,
    TinyFishRateLimiter,
)


def test_search_minute_budget_blocks_until_clock_advances() -> None:
    now = [0.0]
    sleeps: list[float] = []
    limiter = TinyFishRateLimiter(
        TinyFishRateLimitPolicy(
            search_per_minute=2,
            search_per_hour=10,
            fetch_urls_per_minute=10,
            fetch_urls_per_day=100,
        ),
        clock=lambda: now[0],
        wall_clock=lambda: now[0],
        sleep=lambda seconds: (sleeps.append(seconds), now.__setitem__(0, now[0] + seconds)),
    )
    limiter.acquire_search()
    limiter.acquire_search()
    limiter.acquire_search()
    assert sleeps
    assert now[0] >= 60


def test_search_hour_budget_blocks_when_minute_capacity_is_available() -> None:
    now = [0.0]
    sleeps: list[float] = []
    limiter = TinyFishRateLimiter(
        TinyFishRateLimitPolicy(
            search_per_minute=10,
            search_per_hour=2,
            fetch_urls_per_minute=10,
            fetch_urls_per_day=100,
        ),
        clock=lambda: now[0],
        wall_clock=lambda: now[0],
        sleep=lambda seconds: (sleeps.append(seconds), now.__setitem__(0, now[0] + seconds)),
    )
    limiter.acquire_search()
    limiter.acquire_search()
    limiter.acquire_search()
    assert sleeps[-1] >= 3600


def test_fetch_budget_is_counted_in_urls() -> None:
    now = [0.0]
    limiter = TinyFishRateLimiter(
        TinyFishRateLimitPolicy(
            search_per_minute=10,
            search_per_hour=100,
            fetch_urls_per_minute=5,
            fetch_urls_per_day=20,
        ),
        clock=lambda: now[0],
        wall_clock=lambda: now[0],
        sleep=lambda seconds: now.__setitem__(0, now[0] + seconds),
    )
    limiter.acquire_fetch(3)
    limiter.acquire_fetch(3)
    assert now[0] >= 60


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
        raise AssertionError("expected daily Fetch quota failure")
