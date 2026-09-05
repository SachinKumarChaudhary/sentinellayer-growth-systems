import pytest

from sentinellayer_growth_engine.sales import SalesHandoffError, build_sales_handoff


def test_build_interest_handoff():
    out = build_sales_handoff(
        account_id="account-1",
        person_id="person-1",
        trigger_type="positive_reply",
        priority="P1",
        recommended_action="human_follow_up",
        why_now=["Positive reply"],
        latest_reply={"classification": "interested"},
    )
    assert out["priority"] == "P1"
    assert out["recommended_action"] == "human_follow_up"


def test_invalid_priority_rejected():
    with pytest.raises(SalesHandoffError):
        build_sales_handoff(
            account_id="a",
            person_id="p",
            trigger_type="x",
            priority="P5",
            recommended_action="human_follow_up",
        )


def test_sales_task_id_must_be_uuid():
    with pytest.raises(SalesHandoffError):
        build_sales_handoff(
            account_id="a",
            person_id="p",
            trigger_type="x",
            priority="P1",
            recommended_action="human_follow_up",
            sales_task_id="not-a-uuid",
        )
