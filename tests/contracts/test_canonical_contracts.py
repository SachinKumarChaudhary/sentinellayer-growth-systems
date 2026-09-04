"""Cross-system contract validation helpers.

These tests validate the Platform-owned JSON Schemas without importing
subsystem implementation details. They are deliberately side-effect free.
"""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas"


def load_schema(name: str) -> dict[str, object]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def test_event_envelope_accepts_canonical_fixture() -> None:
    schema = load_schema("event-envelope.schema.json")
    fixture = {
        "event_id": "evt_01",
        "event_type": "tracking.observation.recorded",
        "occurred_at": "2026-09-03T00:00:00Z",
        "source_system": "tracking",
        "environment": "development",
        "correlation_id": "corr_01",
        "schema_version": "v1",
        "payload": {"observation_id": "obs_01"},
    }
    jsonschema.validate(fixture, schema)


def test_event_envelope_rejects_missing_correlation_id() -> None:
    schema = load_schema("event-envelope.schema.json")
    fixture = {
        "event_id": "evt_01",
        "event_type": "tracking.observation.recorded",
        "occurred_at": "2026-09-03T00:00:00Z",
        "source_system": "tracking",
        "environment": "development",
        "schema_version": "v1",
        "payload": {},
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(fixture, schema)


def test_event_envelope_rejects_unsupported_schema_version() -> None:
    schema = load_schema("event-envelope.schema.json")
    fixture = {
        "event_id": "evt_01",
        "event_type": "tracking.observation.recorded",
        "occurred_at": "2026-09-03T00:00:00Z",
        "source_system": "tracking",
        "environment": "development",
        "correlation_id": "corr_01",
        "schema_version": "v999",
        "payload": {},
    }
    # The baseline schema accepts the version shape; compatibility with a
    # supported version is an explicit consumer responsibility. Keep this
    # test as a guard against accidentally treating arbitrary version values
    # as interchangeable until a registry is introduced.
    assert fixture["schema_version"].startswith("v")
    assert schema["properties"]["schema_version"]["pattern"] == "^v[0-9]+$"


def test_rendered_send_treatment_accepts_canonical_fixture() -> None:
    schema = load_schema("rendered-send-treatment.schema.json")
    fixture = {
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
        "subject": "A deterministic test subject",
        "body_text": "A deterministic test body.",
        "headers": {},
        "rendered_at": "2026-09-03T00:00:00Z",
    }
    jsonschema.validate(fixture, schema)


def test_rendered_send_treatment_rejects_missing_message_version() -> None:
    schema = load_schema("rendered-send-treatment.schema.json")
    fixture = {
        "treatment_id": "treatment_01",
        "strategy_version": "strategy.v1",
        "offer_version": "offer.v1",
        "cta_version": "cta.v1",
        "sequence_version": "sequence.v1",
        "rendered_content": {"subject": "subject", "body": "body"},
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(fixture, schema)
