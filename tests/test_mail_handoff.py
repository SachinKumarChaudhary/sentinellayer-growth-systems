from datetime import UTC, datetime

import pytest

from sentinellayer_growth_engine.mail_handoff import (
    CampaignMailHandoff,
    CampaignMailHandoffError,
)

U = {
    "campaign": "11111111-1111-4111-8111-111111111111",
    "person": "person-1",
    "step": "22222222-2222-4222-8222-222222222222",
    "mailbox": "33333333-3333-4333-8333-333333333333",
    "send": "44444444-4444-4444-8444-444444444444",
}
T = {
    "schema_version": "1.0",
    "enrollment_id": "55555555-5555-4555-8555-555555555555",
    "campaign_id": U["campaign"],
    "person_id": U["person"],
    "account_id": "account-1",
    "sequence_step_id": U["step"],
    "strategy_version_id": "66666666-6666-4666-8666-666666666666",
    "offer_version_id": "77777777-7777-4777-8777-777777777777",
    "message_version_id": "88888888-8888-4888-8888-888888888888",
    "cta_version_id": "99999999-9999-4999-8999-999999999999",
    "sequence_version_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "recipient_email": "buyer@example.com",
    "subject": "Hello",
    "body_text": "Hello there",
    "headers": {},
    "rendered_at": "2026-09-02T12:00:00+00:00",
}

def test_builds_valid_send_request():
    when = datetime(2026, 9, 2, 12, tzinfo=UTC)
    result = CampaignMailHandoff().build_send_request(
        treatment=T, mailbox_id=U["mailbox"], scheduled_at=when, send_id=U["send"]
    )
    assert result["send_id"] == U["send"]
    assert result["treatment"]["recipient_email"] == "buyer@example.com"
    assert result["idempotency_key"] == f"campaign-send:{U['campaign']}:{U['person']}:{U['step']}"

def test_rejects_invalid_treatment():
    bad = dict(T)
    bad["subject"] = ""
    with pytest.raises(CampaignMailHandoffError, match="invalid treatment"):
        CampaignMailHandoff().build_send_request(
            treatment=bad,
            mailbox_id=U["mailbox"],
            scheduled_at=datetime(2026, 9, 2, 12),
        )

def test_rejects_naive_schedule():
    with pytest.raises(CampaignMailHandoffError, match="timezone-aware"):
        CampaignMailHandoff().build_send_request(
            treatment=T,
            mailbox_id=U["mailbox"],
            scheduled_at=datetime(2026, 9, 2, 12, tzinfo=UTC),
        )

def test_rejects_invalid_mailbox():
    with pytest.raises(CampaignMailHandoffError, match="mailbox_id"):
        CampaignMailHandoff().build_send_request(
            treatment=T,
            mailbox_id="not-a-uuid",
            scheduled_at=datetime(2026, 9, 2, 12, tzinfo=UTC),
        )

def test_idempotency_key_can_be_explicitly_frozen():
    result = CampaignMailHandoff().build_send_request(
        treatment=T,
        mailbox_id=U["mailbox"],
        scheduled_at=datetime(2026, 9, 2, 12, tzinfo=UTC),
        send_id=U["send"],
        idempotency_key="campaign-send:v2:abc",
    )
    assert result["idempotency_key"] == "campaign-send:v2:abc"


def test_campaign_treatment_to_mail_request_preserves_canonical_provenance():
    when = datetime(2026, 9, 3, 12, tzinfo=UTC)
    result = CampaignMailHandoff().build_send_request(
        treatment=T,
        mailbox_id=U["mailbox"],
        scheduled_at=when,
        send_id=U["send"],
    )
    assert result["campaign_id"] == T["campaign_id"]
    assert result["person_id"] == T["person_id"]
    assert result["sequence_step_id"] == T["sequence_step_id"]
    assert result["mailbox_id"] == U["mailbox"]
    assert result["scheduled_at"] == when.isoformat()
    assert result["treatment"] == T


def test_default_idempotency_identity_is_stable_for_same_treatment():
    handoff = CampaignMailHandoff()
    when = datetime(2026, 9, 3, 12, tzinfo=UTC)
    first = handoff.build_send_request(
        treatment=T, mailbox_id=U["mailbox"], scheduled_at=when, send_id=U["send"]
    )
    second = handoff.build_send_request(
        treatment=T, mailbox_id=U["mailbox"], scheduled_at=when, send_id=U["send"]
    )
    assert first["idempotency_key"] == second["idempotency_key"]


def test_explicit_idempotency_key_does_not_change_treatment():
    result = CampaignMailHandoff().build_send_request(
        treatment=T,
        mailbox_id=U["mailbox"],
        scheduled_at=datetime(2026, 9, 3, 12, tzinfo=UTC),
        send_id=U["send"],
        idempotency_key="campaign-send:explicit:v1",
    )
    assert result["treatment"] == T
