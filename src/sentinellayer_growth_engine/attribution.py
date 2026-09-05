from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from .contracts import ContractValidationError, validate_contract


class AttributionError(ValueError):
    pass


def build_attribution_context(
    *,
    account_id: str,
    person_id: str | None,
    campaign_id: str | None = None,
    enrollment_id: str | None = None,
    strategy_version_id: str | None = None,
    offer_version_id: str | None = None,
    message_version_id: str | None = None,
    cta_version_id: str | None = None,
    sequence_version_id: str | None = None,
    experiment_id: str | None = None,
    experiment_variant_id: str | None = None,
    send_id: str | None = None,
) -> dict[str, Any]:
    if not account_id.strip():
        raise AttributionError("account_id is required")
    for name, value in {
        "campaign_id": campaign_id,
        "enrollment_id": enrollment_id,
        "strategy_version_id": strategy_version_id,
        "offer_version_id": offer_version_id,
        "message_version_id": message_version_id,
        "cta_version_id": cta_version_id,
        "sequence_version_id": sequence_version_id,
        "experiment_id": experiment_id,
        "experiment_variant_id": experiment_variant_id,
        "send_id": send_id,
    }.items():
        if value is not None:
            try:
                UUID(value)
            except (ValueError, AttributeError, TypeError) as exc:
                raise AttributionError(f"{name} must be a UUID") from exc

    payload = {
        "schema_version": "1.0",
        "account_id": account_id,
        "person_id": person_id,
        "campaign_id": campaign_id,
        "enrollment_id": enrollment_id,
        "strategy_version_id": strategy_version_id,
        "offer_version_id": offer_version_id,
        "message_version_id": message_version_id,
        "cta_version_id": cta_version_id,
        "sequence_version_id": sequence_version_id,
        "experiment_id": experiment_id,
        "experiment_variant_id": experiment_variant_id,
        "send_id": send_id,
    }
    try:
        return validate_contract("attribution_context", payload)
    except ContractValidationError as exc:
        raise AttributionError(str(exc)) from exc


def build_sales_attribution_event(
    *,
    event_type: str,
    account_id: str,
    person_id: str | None,
    occurred_at: datetime,
    attribution: dict[str, Any],
    event_id: str | None = None,
) -> dict[str, Any]:
    if not event_type.strip():
        raise AttributionError("event_type is required")
    if occurred_at.tzinfo is None:
        raise AttributionError("occurred_at must be timezone-aware")
    context = build_attribution_context(account_id=account_id, person_id=person_id, **{
        k: attribution.get(k) for k in (
            "campaign_id","enrollment_id","strategy_version_id","offer_version_id",
            "message_version_id","cta_version_id","sequence_version_id",
            "experiment_id","experiment_variant_id","send_id"
        )
    })
    return {
        "event_id": event_id or str(uuid4()),
        "event_type": event_type,
        "account_id": account_id,
        "person_id": person_id,
        "occurred_at": occurred_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "attribution": context,
    }
