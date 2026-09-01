from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError

_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "schemas"

CONTRACT_SCHEMAS: dict[str, str] = {
    "account_ref": "account-ref.schema.json",
    "person_ref": "person-ref.schema.json",
    "intent_snapshot": "intent-snapshot.schema.json",
    "campaign_enrollment": "campaign-enrollment.schema.json",
    "rendered_send_treatment": "rendered-send-treatment.schema.json",
    "send_request": "send-request.schema.json",
    "provider_outcome": "provider-outcome.schema.json",
    "tracking_event": "tracking-event.schema.json",
    "conversation_handoff": "conversation-handoff.schema.json",
    "sales_handoff": "sales-handoff.schema.json",
    "attribution_context": "attribution-context.schema.json",
}


class ContractValidationError(ValueError):
    """Raised when a machine contract payload is invalid."""


def _load_schema(contract_name: str) -> dict[str, Any]:
    try:
        filename = CONTRACT_SCHEMAS[contract_name]
    except KeyError as exc:
        raise ValueError(f"unknown contract: {contract_name}") from exc

    path = _SCHEMA_DIR / filename
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"contract schema not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"contract schema is invalid JSON: {path}") from exc

    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise RuntimeError(f"contract schema is not valid JSON Schema: {path}") from exc
    return schema


def validate_contract(contract_name: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and return a shallow copy of a contract payload.

    Validation is intentionally fail-closed. The JSON Schemas are the source of
    truth for machine-facing contract shape and use Draft 2020-12 semantics.
    """
    schema = _load_schema(contract_name)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    try:
        validator.validate(dict(payload))
    except ValidationError as exc:
        path = ".".join(str(part) for part in exc.absolute_path)
        location = f" at {path}" if path else ""
        raise ContractValidationError(
            f"{contract_name} contract validation failed{location}: {exc.message}"
        ) from exc
    return dict(payload)


def validate_rendered_send_treatment(payload: Mapping[str, Any]) -> dict[str, Any]:
    return validate_contract("rendered_send_treatment", payload)


def validate_send_request(payload: Mapping[str, Any]) -> dict[str, Any]:
    return validate_contract("send_request", payload)
