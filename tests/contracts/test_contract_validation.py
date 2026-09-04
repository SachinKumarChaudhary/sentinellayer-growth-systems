from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from jsonschema import Draft202012Validator

from sentinellayer_growth_engine.contracts import (
    CONTRACT_SCHEMAS,
    ContractValidationError,
    _load_schema,
    validate_contract,
    validate_rendered_send_treatment,
    validate_send_request,
)

UTC_NOW = datetime.now(UTC).isoformat().replace("+00:00", "Z")


def uid() -> str:
    return str(uuid4())


def rendered_treatment() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "enrollment_id": uid(),
        "campaign_id": uid(),
        "person_id": "person-001",
        "account_id": "account-001",
        "sequence_step_id": uid(),
        "strategy_version_id": uid(),
        "offer_version_id": uid(),
        "message_version_id": uid(),
        "cta_version_id": uid(),
        "sequence_version_id": uid(),
        "recipient_email": "prospect@example.invalid",
        "subject": "A specific observation",
        "body_text": "Hello, this is a synthetic contract test.",
        "headers": {"X-SL-Test": "true"},
        "rendered_at": UTC_NOW,
        "experiment_id": uid(),
        "experiment_variant_id": uid(),
        "asset": {"type": "none"},
        "personalization": {"evidence_id": "synthetic-001"},
        "reply_to": "sender@example.invalid",
    }


def contract_fixtures() -> dict[str, dict[str, object]]:
    campaign_id = uid()
    account_id = "account-001"
    person_id = "person-001"
    enrollment_id = uid()
    strategy_id = uid()
    offer_id = uid()
    sequence_id = uid()
    step_id = uid()
    send_id = uid()

    return {
        "account_ref": {
            "schema_version": "1.0",
            "account_id": account_id,
            "domain": "example.invalid",
            "account_name": "Synthetic Example",
            "qualification_status": "qualified",
            "source": "synthetic",
        },
        "person_ref": {
            "schema_version": "1.0",
            "person_id": person_id,
            "account_id": account_id,
            "email": "prospect@example.invalid",
            "name": "Synthetic Prospect",
            "title": "CTO",
            "contactability_status": "verified",
        },
        "intent_snapshot": {
            "schema_version": "1.0",
            "account_id": account_id,
            "person_id": person_id,
            "fit_score": 9,
            "intent_score": 8,
            "priority": "P1",
            "negative_flags": [],
            "behavior_flags": ["synthetic_signal"],
            "evidence": [{"type": "synthetic", "source": "test"}],
            "calculated_at": UTC_NOW,
            "model_version": "test-model-1",
        },
        "campaign_enrollment": {
            "schema_version": "1.0",
            "enrollment_id": enrollment_id,
            "campaign_id": campaign_id,
            "account_id": account_id,
            "person_id": person_id,
            "priority_at_enrollment": "P1",
            "strategy_version_id": strategy_id,
            "offer_version_id": offer_id,
            "sequence_version_id": sequence_id,
            "experiment_id": None,
            "experiment_variant_id": None,
            "enrolled_at": UTC_NOW,
            "status": "active",
        },
        "rendered_send_treatment": rendered_treatment(),
        "send_request": {
            "schema_version": "1.0",
            "send_id": send_id,
            "idempotency_key": f"{campaign_id}:{person_id}:{step_id}",
            "campaign_id": campaign_id,
            "person_id": person_id,
            "sequence_step_id": step_id,
            "mailbox_id": uid(),
            "scheduled_at": UTC_NOW,
            "treatment": {
                "schema_version": "1.0",
                "enrollment_id": enrollment_id,
                "campaign_id": campaign_id,
                "person_id": person_id,
                "account_id": account_id,
                "sequence_step_id": step_id,
                "strategy_version_id": strategy_id,
                "offer_version_id": offer_id,
                "message_version_id": uid(),
                "cta_version_id": uid(),
                "sequence_version_id": sequence_id,
                "recipient_email": "prospect@example.invalid",
                "subject": "A specific observation",
                "body_text": "Hello, this is a synthetic contract test.",
                "headers": {"X-SL-Test": "true"},
                "rendered_at": UTC_NOW,
                "experiment_id": None,
                "experiment_variant_id": None,
                "asset": {"type": "none"},
                "personalization": {"evidence_id": "synthetic-001"},
                "reply_to": "sender@example.invalid"
            },
        },
        "provider_outcome": {
            "schema_version": "1.0",
            "send_id": send_id,
            "attempt_id": uid(),
            "provider": "mock",
            "outcome_type": "accepted",
            "occurred_at": UTC_NOW,
            "provider_message_id": "<synthetic@example.invalid>",
        },
        "tracking_event": {
            "event_id": uid(),
            "schema_version": "1.0",
            "event_type": "link_clicked",
            "occurred_at": UTC_NOW,
            "source_system": "tracking",
            "environment": "development",
            "account_id": account_id,
            "person_id": person_id,
            "campaign_id": campaign_id,
            "send_id": send_id,
            "correlation_id": "synthetic-correlation-001",
            "confidence": 0.9,
            "payload": {"synthetic": True},
        },
        "conversation_handoff": {
            "schema_version": "1.0",
            "conversation_id": uid(),
            "reply_id": uid(),
            "account_id": account_id,
            "person_id": person_id,
            "source_send_id": send_id,
            "classification": "interested",
            "conversation_state": "classified",
            "recommended_action": "human_follow_up",
            "intent_snapshot": {"priority": "P1"},
            "timeline": [],
            "commitments": [],
            "objections": [],
            "questions": [],
            "evidence": [{"source": "synthetic"}],
            "created_at": UTC_NOW,
        },
        "sales_handoff": {
            "schema_version": "1.0",
            "sales_task_id": uid(),
            "account_id": account_id,
            "person_id": person_id,
            "trigger_type": "positive_reply",
            "priority": "P1",
            "recommended_action": "contact_within_one_business_day",
            "why_now": [{"source": "synthetic"}],
            "latest_reply": {"classification": "interested"},
            "behavior_summary": [],
            "campaign_context": {"campaign_id": campaign_id},
            "conversation_summary": {"state": "classified"},
            "created_at": UTC_NOW,
        },
        "attribution_context": {
            "schema_version": "1.0",
            "account_id": account_id,
            "person_id": person_id,
            "campaign_id": campaign_id,
            "enrollment_id": enrollment_id,
            "strategy_version_id": strategy_id,
            "offer_version_id": offer_id,
            "message_version_id": uid(),
            "cta_version_id": uid(),
            "sequence_version_id": sequence_id,
            "experiment_id": None,
            "experiment_variant_id": None,
            "send_id": send_id,
        },
    }


@pytest.mark.parametrize("contract_name", sorted(CONTRACT_SCHEMAS))
def test_all_contract_schemas_are_valid_json_schema(contract_name: str) -> None:
    schema = _load_schema(contract_name)
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("contract_name", sorted(CONTRACT_SCHEMAS))
def test_valid_contract_fixture_passes(contract_name: str) -> None:
    payload = contract_fixtures()[contract_name]
    assert validate_contract(contract_name, payload) == payload


@pytest.mark.parametrize("contract_name", sorted(CONTRACT_SCHEMAS))
def test_required_field_is_fail_closed(contract_name: str) -> None:
    payload = dict(contract_fixtures()[contract_name])
    schema = _load_schema(contract_name)
    required = schema["required"][0]
    payload.pop(required)

    with pytest.raises(ContractValidationError):
        validate_contract(contract_name, payload)


def test_additional_properties_are_rejected() -> None:
    payload = rendered_treatment()
    payload["unexpected"] = True

    with pytest.raises(ContractValidationError, match="Additional properties"):
        validate_rendered_send_treatment(payload)


def test_send_request_rejects_invalid_nested_treatment() -> None:
    payload = dict(contract_fixtures()["send_request"])
    treatment = dict(payload["treatment"])
    treatment.pop("recipient_email")
    payload["treatment"] = treatment

    with pytest.raises(ContractValidationError):
        validate_send_request(payload)


def test_send_request_preserves_cross_system_identity() -> None:
    payload = contract_fixtures()["send_request"]
    treatment = payload["treatment"]

    assert payload["campaign_id"] == treatment["campaign_id"]
    assert payload["person_id"] == treatment["person_id"]
    assert payload["sequence_step_id"] == treatment["sequence_step_id"]
    assert validate_send_request(payload)["treatment"] == treatment


def test_tracking_and_sales_preserve_account_and_person_identity() -> None:
    fixtures = contract_fixtures()
    tracking = fixtures["tracking_event"]
    sales = fixtures["sales_handoff"]

    assert tracking["account_id"] == sales["account_id"]
    assert tracking["person_id"] == sales["person_id"]
