from __future__ import annotations

from collections.abc import Mapping, Protocol
from dataclasses import dataclass
from datetime import datetime
from typing import Any

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


class LinkedInExecutionPersistence(Protocol):
    """Persistence boundary used after provider execution."""

    def record_execution_attempt(
        self,
        *,
        touchpoint_id: str,
        provider: str | None,
        result: str,
        provider_error_code: str | None,
        started_at: datetime | None,
        finished_at: datetime | None,
        metadata: Mapping[str, Any],
    ) -> int:
        ...

    def record_touchpoint_observation(
        self,
        *,
        touchpoint_id: str,
        status: str,
        provider: str,
        provider_reference: str | None,
        metadata: Mapping[str, Any],
        executed_at: datetime | None,
    ) -> None:
        ...


def execute_touchpoint(
    *,
    provider: LinkedInProvider,
    contact: LinkedInContact,
    touchpoint: LinkedInTouchpoint,
    now: datetime,
) -> ExecutionResult:
    """Execute one already-approved LinkedIn touchpoint through a provider."""
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


def execute_and_persist_touchpoint(
    *,
    provider: LinkedInProvider,
    contact: LinkedInContact,
    touchpoint: LinkedInTouchpoint,
    now: datetime,
    persistence: LinkedInExecutionPersistence,
) -> ExecutionResult:
    """Execute a touchpoint and persist only provider-observed execution facts."""
    try:
        result = execute_touchpoint(
            provider=provider,
            contact=contact,
            touchpoint=touchpoint,
            now=now,
        )
    except LinkedInExecutionError as exc:
        persistence.record_execution_attempt(
            touchpoint_id=touchpoint.touchpoint_id,
            provider=type(provider).__name__,
            result="failed",
            provider_error_code=None,
            started_at=now,
            finished_at=now,
            metadata={"error": str(exc)},
        )
        raise

    persistence.record_execution_attempt(
        touchpoint_id=touchpoint.touchpoint_id,
        provider=result.provider,
        result=result.status,
        provider_error_code=None,
        started_at=now,
        finished_at=result.executed_at,
        metadata=result.metadata,
    )

    if result.status in {"sent", "delivered"}:
        persistence.record_touchpoint_observation(
            touchpoint_id=touchpoint.touchpoint_id,
            status=result.status,
            provider=result.provider,
            provider_reference=result.provider_reference,
            metadata=result.metadata,
            executed_at=result.executed_at,
        )
    return result
