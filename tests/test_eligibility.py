from datetime import UTC, datetime, timedelta

from sentinellayer_growth_engine.eligibility import LeadEligibility, is_due


def test_due_check_uses_absolute_time() -> None:
    now = datetime.now(UTC)
    assert is_due(now - timedelta(seconds=1), now) is True
    assert is_due(now + timedelta(seconds=1), now) is False


def test_eligibility_fails_closed_on_any_blocker() -> None:
    base = LeadEligibility(
        suppressed=False,
        replied=False,
        campaign_active=True,
        mailbox_active=True,
        mailbox_health_ok=True,
        due=True,
        within_daily_limit=True,
    )
    assert base.allowed is True

    blocked = base.__class__(**{**base.__dict__, "suppressed": True})
    assert blocked.allowed is False
