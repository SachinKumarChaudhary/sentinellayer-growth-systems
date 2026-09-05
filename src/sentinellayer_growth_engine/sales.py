from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from .contracts import ContractValidationError, validate_contract


class SalesHandoffError(ValueError):
    pass


def build_sales_handoff(
    *,
    account_id: str,
    person_id: str,
    trigger_type: str,
    priority: str,
    recommended_action: str,
    why_now: list[Any] | None = None,
    latest_reply: dict[str, Any] | None = None,
    behavior_summary: list[Any] | None = None,
    campaign_context: dict[str, Any] | None = None,
    conversation_summary: dict[str, Any] | None = None,
    sales_task_id: str | None = None,
) -> dict[str, Any]:
    if not account_id.strip() or not person_id.strip():
        raise SalesHandoffError("account_id and person_id are required")
    if priority not in {"P1", "P2", "P3", "P4"}:
        raise SalesHandoffError("priority must be P1/P2/P3/P4")
    if not trigger_type.strip() or not recommended_action.strip():
        raise SalesHandoffError("trigger_type and recommended_action are required")
    task_id = sales_task_id or str(uuid4())
    try:
        UUID(task_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise SalesHandoffError("sales_task_id must be a UUID") from exc

    payload = {
        "schema_version": "1.0",
        "sales_task_id": task_id,
        "account_id": account_id,
        "person_id": person_id,
        "trigger_type": trigger_type,
        "priority": priority,
        "recommended_action": recommended_action,
        "why_now": why_now or [],
        "latest_reply": latest_reply,
        "behavior_summary": behavior_summary,
        "campaign_context": campaign_context,
        "conversation_summary": conversation_summary,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    try:
        return validate_contract("sales_handoff", payload)
    except ContractValidationError as exc:
        raise SalesHandoffError(f"invalid SalesHandoff: {exc}") from exc
