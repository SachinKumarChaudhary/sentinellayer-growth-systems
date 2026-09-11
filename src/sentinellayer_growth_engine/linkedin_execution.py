from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from .linkedin_outreach import LinkedInContact, LinkedInProvider, LinkedInTouchpoint, OperatorProvider


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    provider: str
    provider_reference: str | None
    metadata: Mapping[str, Any]
    executed_at: datetime | None


class LinkedInExecutionError(ValueError):
    """Raised when a LinkedIn touchpoint cannot be executed safely."""


def execute_touchpoint(
    *,
    provider: LinkedInProvider,
    contact: LinkedInContact,
    touchpoint: LinkedInTouchpoint,
    now: datetime,
) -> ExecutionResult:
    """Execute one already-approved LinkedIn touchpoint through a provider.

    The function deliberately has no database side effects. Callers persist the
    returned provider result and execution attempt in the canonical tables.
    OperatorProvider is the default safe path when no real provider capability
    exists; it never claims that an action was sent.
    """
    if now.tzinfo is None:
        raise LinkedInExecutionError("now must be timezone-aware")
    if touchpoint.channel != "linkedin":
        raise LinkedInExecutionError("touchpoint channel must be linkedin")
    if touchpoint.status not in {"planned", "approved", "queued"}:
        raise LinkedInExecutionError(f"touchpoint is not executable from state {touchpoint.status!r}")
    if touchpoint.metadata.get("linkedin_url") != contact.linkedin_url:
        raise LinkedInExecutionError("touchpoint LinkedIn URL does not match contact")

    capabilities = provider.capabilities()
    action = touchpoint.touchpoint_type
    message = str(touchpoint.metadata.get("message") or "")

    if action == "operator_review":
        return ExecutionResult(
            status="operator_required",
            provider="operator",
            provider_reference=None,
            metadata={"action": action, "reason": "operator_review_required"},
            executed_at=None,
        )

    required_capability = {
        "connection_request": "linkedin.connection_request",
        "message": "linkedin.message",
        "follow_up": "linkedin.message",
    }.get(action)
    if required_capability is None:
        raise LinkedInExecutionError(f"unsupported touchpoint type: {action!r}")

    if required_capability not in capabilities:
        # Never call a provider method that it has not declared capable of.
        operator = OperatorProvider()
        result = (
            operator.send_connection_request(linkedin_url=contact.linkedin_url, message=message)
            if action == "connection_request"
            else operator.send_message(linkedin_url=contact.linkedin_url, message=message)
        )
        return ExecutionResult(
            status="operator_required",
            provider="operator",
            provider_reference=None,
            metadata=dict(result),
            executed_at=None,
        )

    result = (
        provider.send_connection_request(linkedin_url=contact.linkedin_url, message=message)
        if action == "connection_request"
        else provider.send_message(linkedin_url=contact.linkedin_url, message=message)
    )
    status = str(result.get("status", "sent")).strip().lower()
    if status not in {"sent", "delivered"}:
        raise LinkedInExecutionError(f"provider returned non-delivery status: {status!r}")
    provider_reference = result.get("provider_reference")
    return ExecutionResult(
        status=status,
        provider="linkedin_provider",
        provider_reference=str(provider_reference) if provider_reference is not None else None,
        metadata=dict(result),
        executed_at=now,
    )
