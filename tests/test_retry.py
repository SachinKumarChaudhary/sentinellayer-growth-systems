from datetime import datetime, timezone

from sentinellayer_growth_engine.retry import RetryPolicy


def test_retry_policy_exhausts_after_max_attempts() -> None:
    policy = RetryPolicy(max_attempts=3)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    assert policy.next_attempt_at(attempt=3, now=now) is None


def test_retry_policy_uses_exponential_backoff() -> None:
    policy = RetryPolicy(base_delay_seconds=60, max_delay_seconds=3600)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    assert policy.next_attempt_at(attempt=1, now=now).second == 0
    assert (policy.next_attempt_at(attempt=1, now=now) - now).total_seconds() == 60
    assert (policy.next_attempt_at(attempt=2, now=now) - now).total_seconds() == 120
