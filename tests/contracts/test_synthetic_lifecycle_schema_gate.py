"""Fixture-only cross-system schema and identity gate."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]


def schema(name: str) -> dict[str, object]:
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def test_campaign_mail_tracking_lifecycle_preserves_identity() -> None:
    treatment = {
        "schema_version": "1.0",
        "enrollment_id": "11111111-1111-4111-8111-111111111111",
        "campaign_id": "22222222-2222-4222-8222-222222222222",
        "person_id": "person-001",
        "account_id": "account-001",
        "sequence_step_id": "33333333-3333-4333-8333-333333333333",
        "strategy_version_id": "44444444-4444-4444-8444-444444444444",
        "offer_version_id": "55555555-5555-4555-8555-555555555555",
        "message_version_id": "66666666-6666-4666-8666-666666666666",
        "cta_version_id": "77777777-7777-4777-8777-777777777777",
        "sequence_version_id": "88888888-8888-4888-8888-888888888888",
        "recipient_email": "prospect@example.invalid",
        "subject": "Synthetic subject",
        "body_text": "Synthetic body",
        "headers": {},
        "rendered_at": "2026-09-05T00:00:00Z",
    }
    jsonschema.validate(treatment, schema("rendered-send-treatment.schema.json"))

    send_request = {
        "schema_version": "1.0",
        "send_id": "99999999-9999-4999-8999-999999999999",
        "idempotency_key": "campaign:person:step",
        "campaign_id": treatment["campaign_id"],
        "person_id": treatment["person_id"],
        "sequence_step_id": treatment["sequence_step_id"],
        "mailbox_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "scheduled_at": treatment["rendered_at"],
        "treatment": treatment,
    }
    jsonschema.validate(send_request, schema("send-request.schema.json"))

    provider_outcome = {
        "schema_version": "1.0",
        "send_id": send_request["send_id"],
        "attempt_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "provider": "mock",
        "outcome_type": "accepted",
        "occurred_at": treatment["rendered_at"],
        "provider_message_id": "<synthetic@example.invalid>",
    }
    jsonschema.validate(provider_outcome, schema("provider-outcome.schema.json"))

    tracking_event = {
        "event_id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "schema_version": "1.0",
        "event_type": "link_clicked",
        "occurred_at": treatment["rendered_at"],
        "source_system": "tracking",
        "environment": "development",
        "account_id": treatment["account_id"],
        "person_id": treatment["person_id"],
        "campaign_id": treatment["campaign_id"],
        "send_id": send_request["send_id"],
        "correlation_id": "corr-001",
        "confidence": 0.9,
        "payload": {
            "provider_message_id": provider_outcome["provider_message_id"],
            "source_event": provider_outcome["send_id"],
        },
    }
    jsonschema.validate(tracking_event, schema("tracking-event.schema.json"))

    assert send_request["campaign_id"] == treatment["campaign_id"]
    assert send_request["person_id"] == treatment["person_id"]
    assert provider_outcome["send_id"] == send_request["send_id"]
    assert tracking_event["send_id"] == send_request["send_id"]
    assert tracking_event["correlation_id"] == "corr-001"


def test_missing_required_cross_system_identity_fails_closed() -> None:
    bad = {
        "event_id": "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        "schema_version": "1.0",
        "event_type": "link_clicked",
        "occurred_at": "2026-09-05T00:00:00Z",
        "source_system": "tracking",
        "environment": "development",
        "payload": {},
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema("tracking-event.schema.json"))
