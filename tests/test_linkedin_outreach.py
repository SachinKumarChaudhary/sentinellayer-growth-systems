from datetime import UTC, datetime, timedelta

import pytest

from sentinellayer_growth_engine.linkedin_outreach import (
    LinkedInContact,
    LinkedInOutreachError,
    next_state_after_observation,
    validate_sequence,
    build_touchpoints,
)


DM = LinkedInContact(
    decision_maker_id="11111111-1111-4111-8111-111111111111",
    company_id=123,
    full_name="Jane Doe",
    title="CISO",
    linkedin_url="https://www.linkedin.com/in/jane-doe",
)
SEQUENCE_ID = "22222222-2222-4222-8222-222222222222"
START = datetime(2026, 9, 11, 12, tzinfo=UTC)


def test_linkedin_contact_rejects_non_profile_urls():
    with pytest.raises(LinkedInOutreachError):
        LinkedInContact(
            decision_maker_id=DM.decision_maker_id,
            company_id=DM.company_id,
            full_name=DM.full_name,
            title=DM.title,
            linkedin_url="https://www.linkedin.com/company/example",
        )


def test_validate_sequence_requires_contiguous_steps_and_message_content():
    steps = validate_sequence(
        [
            {"step_no": 1, "action": "connection_request", "delay_days": 0, "message": "Hello Jane"},
            {"step_no": 2, "action": "message", "delay_days": 2, "message": "Following up"},
        ]
    )
    assert [step.step_no for step in steps] == [1, 2]
    with pytest.raises(LinkedInOutreachError):
        validate_sequence(
            [
                {"step_no": 1, "action": "connection_request", "message": "Hello"},
                {"step_no": 3, "action": "message", "message": "Hello again"},
            ]
        )


def test_build_touchpoints_is_idempotent_by_sequence_step_key():
    steps = validate_sequence(
        [
            {"step_no": 1, "action": "connection_request", "delay_days": 0, "message": "Hello Jane"},
            {"step_no": 2, "action": "follow_up", "delay_days": 4, "message": "Quick follow-up"},
        ]
    )
    points = build_touchpoints(contact=DM, sequence_id=SEQUENCE_ID, steps=steps, start_at=START)
    assert len(points) == 2
    assert points[0].idempotency_key == (
        "linkedin:22222222-2222-4222-8222-222222222222:"
        "11111111-1111-4111-8111-111111111111:1"
    )
    assert points[1].scheduled_at == START + timedelta(days=4)
    assert points[0].metadata["linkedin_url"] == DM.linkedin_url


def test_observed_inbound_response_stops_follow_up():
    result = next_state_after_observation(
        current_state="awaiting_reply",
        observation={"inbound_message": True},
        now=START + timedelta(days=4),
        next_action_at=START + timedelta(days=4),
    )
    assert result.state == "replied"
    assert result.next_action_at is None


def test_no_inbound_before_due_window_does_not_fake_a_no_reply():
    result = next_state_after_observation(
        current_state="awaiting_reply",
        observation={},
        now=START + timedelta(days=2),
        next_action_at=START + timedelta(days=4),
    )
    assert result.state == "awaiting_reply"


def test_due_window_becomes_follow_up_due_only_at_scheduled_time():
    result = next_state_after_observation(
        current_state="awaiting_reply",
        observation={},
        now=START + timedelta(days=4),
        next_action_at=START + timedelta(days=4),
    )
    assert result.state == "follow_up_due"
    assert "without_inbound" in result.reason


def test_acceptance_and_explicit_outcomes_are_observable_events():
    accepted = next_state_after_observation(
        current_state="awaiting_reply",
        observation={"event": "connection_accepted"},
        now=START,
        next_action_at=START,
    )
    assert accepted.state == "active"

    meeting = next_state_after_observation(
        current_state="replied",
        observation={"event": "meeting_booked"},
        now=START,
        next_action_at=None,
    )
    assert meeting.state == "meeting"

    closed = next_state_after_observation(
        current_state="meeting",
        observation={"event": "closed"},
        now=START,
        next_action_at=None,
    )
    assert closed.state == "closed"
