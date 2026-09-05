from datetime import UTC, datetime

import pytest

from sentinellayer_growth_engine.campaign_execution import (
    CampaignExecutionError,
    CampaignExecutionOrchestrator,
)


class FakeCampaignDB:
    def __init__(self, claim=None):
        self.claim = claim
        self.released = []

    def claim_step(self, enrollment_id, worker_id, lease_seconds=300):
        return self.claim

    def release_step(self, enrollment_id, claim_token):
        self.released.append((enrollment_id, claim_token))
        return True


U = {
    "enrollment_id": "11111111-1111-4111-8111-111111111111",
    "campaign_id": "22222222-2222-4222-8222-222222222222",
    "step_id": "33333333-3333-4333-8333-333333333333",
    "strategy": "44444444-4444-4444-8444-444444444444",
    "offer": "55555555-5555-4555-8555-555555555555",
    "sequence": "66666666-6666-4666-8666-666666666666",
    "message": "77777777-7777-4777-8777-777777777777",
    "cta": "88888888-8888-4888-8888-888888888888",
    "mailbox": "99999999-9999-4999-8999-999999999999",
}


def claim():
    return {
        "enrollment_id": U["enrollment_id"],
        "campaign_id": U["campaign_id"],
        "person_id": "person-1",
        "account_id": "account-1",
        "sequence_step_id": U["step_id"],
        "strategy_version_id": U["strategy"],
        "offer_version_id": U["offer"],
        "sequence_version_id": U["sequence"],
        "experiment_variant_id": None,
        "step_claim_token": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "message_version_id": U["message"],
        "cta_version_id": U["cta"],
        "asset_policy": {},
        "channel": "email",
        "recipient_email": "buyer@example.com",
        "step_no": 1,
        "delay_days": 2,
    }


MESSAGE = {
    "status": "active",
    "qa_status": "approved",
    "subject_template": "Hello {{first_name}}",
    "body_template": "We noticed {{signal}}. {{cta.label}}",
    "evidence_requirements": {"required": ["signal"]},
}
CTA = {"status": "active", "label": "Compare notes?", "target": "reply"}


def test_claim_render_handoff_produces_send_request_without_delivery():
    db = FakeCampaignDB(claim())
    out = CampaignExecutionOrchestrator(db).build_send_request(
        enrollment_id=U["enrollment_id"],
        worker_id="worker-1",
        mailbox_id=U["mailbox"],
        scheduled_at=datetime(2026, 9, 5, 12, tzinfo=UTC),
        message_version=MESSAGE,
        cta_version=CTA,
        personalization={"first_name": "Jane"},
        evidence={"signal": "security hiring"},
    )
    assert out["campaign_id"] == U["campaign_id"]
    assert out["person_id"] == "person-1"
    assert out["sequence_step_id"] == U["step_id"]
    assert out["treatment"]["subject"] == "Hello Jane"
    assert out["treatment"]["body_text"] == "We noticed security hiring. Compare notes?"
    assert db.released == []


def test_claim_failure_releases_lease():
    db = FakeCampaignDB(claim())
    with pytest.raises(CampaignMailHandoffError):
        CampaignExecutionOrchestrator(db).build_send_request(
            enrollment_id=U["enrollment_id"],
            worker_id="worker-1",
            mailbox_id="not-a-uuid",
            scheduled_at=datetime(2026, 9, 5, 12, tzinfo=UTC),
            message_version=MESSAGE,
            cta_version=CTA,
            personalization={"first_name": "Jane"},
            evidence={"signal": "security hiring"},
        )
    assert db.released == [(U["enrollment_id"], "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")]


def test_unclaimable_step_fails():
    db = FakeCampaignDB(None)
    with pytest.raises(CampaignExecutionError):
        CampaignExecutionOrchestrator(db).build_send_request(
            enrollment_id=U["enrollment_id"],
            worker_id="worker-1",
            mailbox_id=U["mailbox"],
            scheduled_at=datetime(2026, 9, 5, 12, tzinfo=UTC),
            message_version=MESSAGE,
            cta_version=CTA,
            personalization={"first_name": "Jane"},
            evidence={"signal": "security hiring"},
        )
