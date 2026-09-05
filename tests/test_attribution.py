from datetime import UTC, datetime

import pytest

from sentinellayer_growth_engine.attribution import (
    AttributionError,
    build_attribution_context,
    build_sales_attribution_event,
)


def test_context_preserves_campaign_lineage():
    out = build_attribution_context(
        account_id="a",
        person_id="p",
        campaign_id="11111111-1111-4111-8111-111111111111",
        enrollment_id="22222222-2222-4222-8222-222222222222",
        strategy_version_id="33333333-3333-4333-8333-333333333333",
    )
    assert out["campaign_id"] is not None
    assert out["strategy_version_id"] is not None


def test_invalid_lineage_rejected():
    with pytest.raises(AttributionError):
        build_attribution_context(account_id="a", person_id="p", campaign_id="bad")


def test_sales_event_is_timestamped_and_attributable():
    out = build_sales_attribution_event(
        event_type="meeting_booked",
        account_id="a",
        person_id="p",
        occurred_at=datetime(2026, 9, 5, 12, tzinfo=UTC),
        attribution={"campaign_id":"11111111-1111-4111-8111-111111111111"},
    )
    assert out["event_type"] == "meeting_booked"
    assert out["attribution"]["campaign_id"] == "11111111-1111-4111-8111-111111111111"
