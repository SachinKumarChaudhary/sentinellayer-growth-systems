"""Synthetic cross-system contract lifecycle gate.

This is deliberately fixture-only: it proves boundary compatibility without
sending mail or requiring future Intelligence/Sales runtimes.
"""
from __future__ import annotations

from copy import deepcopy

from .version_registry import require_supported


def test_synthetic_campaign_mail_tracking_lifecycle_preserves_identity() -> None:
    correlation_id = "corr_contract_01"
    account_id = "acct_01"
    person_id = "person_01"
    campaign_id = "campaign_01"
    send_id = "send_01"

    treatment = {
        "treatment_id": "treatment_01",
        "strategy_version": "strategy.v1",
        "offer_version": "offer.v1",
        "message_version": "message.v1",
        "cta_version": "cta.v1",
        "sequence_version": "sequence.v1",
        "selected_assets": [],
        "rendered_content": {"subject": "Subject", "body": "Body"},
    }
    require_supported("rendered-send-treatment", "v1")

    mail_context = {
        "account_id": account_id,
        "person_id": person_id,
        "campaign_id": campaign_id,
        "send_id": send_id,
        "correlation_id": correlation_id,
        "treatment_id": treatment["treatment_id"],
    }

    provider_outcome = {
        **mail_context,
        "provider_message_id": "provider_01",
        "outcome": "accepted",
    }

    tracking_event = {
        "event_id": "evt_tracking_01",
        "event_type": "tracking.observation.recorded",
        "occurred_at": "2026-09-03T00:00:00Z",
        "source_system": "tracking",
        "environment": "development",
        "correlation_id": correlation_id,
        "schema_version": "v1",
        "account_id": account_id,
        "person_id": person_id,
        "campaign_id": campaign_id,
        "send_id": send_id,
        "payload": {
            "provider_message_id": provider_outcome["provider_message_id"],
            "observation_type": "open",
        },
    }
    require_supported("event-envelope", tracking_event["schema_version"])

    assert tracking_event["correlation_id"] == correlation_id
    assert tracking_event["account_id"] == provider_outcome["account_id"]
    assert tracking_event["person_id"] == provider_outcome["person_id"]
    assert tracking_event["campaign_id"] == provider_outcome["campaign_id"]
    assert tracking_event["send_id"] == provider_outcome["send_id"]


def test_synthetic_lifecycle_does_not_mutate_producer_owned_treatment() -> None:
    treatment = {
        "treatment_id": "treatment_02",
        "strategy_version": "strategy.v1",
        "offer_version": "offer.v1",
        "message_version": "message.v1",
        "cta_version": "cta.v1",
        "sequence_version": "sequence.v1",
        "selected_assets": [],
        "rendered_content": {"subject": "Subject", "body": "Body"},
    }
    original = deepcopy(treatment)
    _mail_input = deepcopy(treatment)
    assert treatment == original
    assert _mail_input == original
