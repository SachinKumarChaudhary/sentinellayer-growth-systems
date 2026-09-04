"""Fixture-only synthetic lifecycle across the current system boundaries."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]


def _schema(name: str) -> dict[str, object]:
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def test_synthetic_campaign_mail_tracking_chain_validates() -> None:
    treatment = {
        "treatment_id": "treatment-001",
        "strategy_version": "strategy-001",
        "offer_version": "offer-001",
        "message_version": "message-001",
        "cta_version": "cta-001",
        "sequence_version": "sequence-001",
        "selected_assets": [],
        "rendered_content": {
            "subject": "Synthetic subject",
            "body": "Synthetic body",
        },
    }
    jsonschema.validate(treatment, _schema("rendered-send-treatment.schema.json"))

    envelope = {
        "event_id": "event-001",
        "event_type": "mail.provider.outcome",
        "occurred_at": "2026-09-04T00:00:00Z",
        "source_system": "mail",
        "environment": "development",
        "account_id": "acct-001",
        "person_id": "person-001",
        "campaign_id": "campaign-001",
        "send_id": "send-001",
        "correlation_id": "corr-001",
        "schema_version": "v1",
        "payload": {
            "treatment_id": treatment["treatment_id"],
            "provider_message_id": "provider-001",
            "outcome": "accepted",
        },
    }
    jsonschema.validate(envelope, _schema("event-envelope.schema.json"))

    # Identity/correlation must survive the synthetic boundary chain.
    tracking = dict(envelope)
    tracking["event_id"] = "event-002"
    tracking["event_type"] = "tracking.link.observed"
    tracking["source_system"] = "tracking"
    tracking["payload"] = {
        "source_event_id": envelope["event_id"],
        "observation": "link_clicked",
    }
    jsonschema.validate(tracking, _schema("event-envelope.schema.json"))

    assert tracking["correlation_id"] == envelope["correlation_id"]
    assert tracking["account_id"] == envelope["account_id"]
    assert tracking["person_id"] == envelope["person_id"]
    assert tracking["campaign_id"] == envelope["campaign_id"]
    assert tracking["send_id"] == envelope["send_id"]


def test_synthetic_lifecycle_rejects_missing_required_identity() -> None:
    envelope = {
        "event_id": "event-bad",
        "event_type": "mail.provider.outcome",
        "occurred_at": "2026-09-04T00:00:00Z",
        "source_system": "mail",
        "environment": "development",
        "schema_version": "v1",
        "payload": {},
    }
    import pytest

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(envelope, _schema("event-envelope.schema.json"))
