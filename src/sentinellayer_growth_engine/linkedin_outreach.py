from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Mapping, Protocol, Sequence
from urllib.parse import urlparse
from uuid import UUID, uuid4


LINKEDIN_CHANNEL = "linkedin"


class LinkedInOutreachError(ValueError):
    """Raised when a LinkedIn outreach action is unsafe or invalid."""


@dataclass(frozen=True)
class LinkedInContact:
    decision_maker_id: str
    company_id: int
    full_name: str
    title: str | None
    linkedin_url: str

    def __post_init__(self) -> None:
        try:
            UUID(self.decision_maker_id)
        except ValueError as exc:
            raise LinkedInOutreachError("decision_maker_id must be a UUID") from exc
        if self.company_id <= 0:
            raise LinkedInOutreachError("company_id must be positive")
        if not self.full_name.strip():
            raise LinkedInOutreachError("full_name must not be empty")
        parsed = urlparse(self.linkedin_url)
        if parsed.scheme != "https" or parsed.netloc.lower() not in {"linkedin.com", "www.linkedin.com"}:
            raise LinkedInOutreachError("linkedin_url must be an https LinkedIn URL")
        if "/in/" not in parsed.path.lower():
            raise LinkedInOutreachError("linkedin_url must point to a LinkedIn member profile")


@dataclass(frozen=True)
class SequenceStep:
    step_no: int
    action: str
    delay_days: int
    message: str | None = None

    def __post_init__(self) -> None:
        if self.step_no < 1:
            raise LinkedInOutreachError("step_no must be positive")
        if self.delay_days < 0:
            raise LinkedInOutreachError("delay_days must not be negative")
        allowed = {"connection_request", "message", "follow_up", "operator_review"}
        if self.action not in allowed:
            raise LinkedInOutreachError(f"unsupported LinkedIn sequence action: {self.action}")
        if self.action in {"connection_request", "message", "follow_up"} and not (self.message or "").strip():
            raise LinkedInOutreachError(f"{self.action} requires message text")


@dataclass(frozen=True)
class LinkedInTouchpoint:
    touchpoint_id: str
    decision_maker_id: str
    company_id: int
    channel: str
    touchpoint_type: str
    status: str
    scheduled_at: datetime
    idempotency_key: str
    metadata: Mapping[str, Any]


@dataclass(frozen=True)
class StateUpdate:
    state: str
    next_action_at: datetime | None
    reason: str


class LinkedInProvider(Protocol):
    """Capability boundary for any concrete LinkedIn execution provider."""

    def capabilities(self) -> set[str]: ...

    def send_connection_request(self, *, linkedin_url: str, message: str) -> Mapping[str, Any]: ...

    def send_message(self, *, linkedin_url: str, message: str) -> Mapping[str, Any]: ...

    def observe(self, *, linkedin_url: str) -> Mapping[str, Any]: ...


class OperatorProvider:
    """Default safe provider: emits operator tasks instead of performing actions."""

    def capabilities(self) -> set[str]:
        return set()

    def send_connection_request(self, *, linkedin_url: str, message: str) -> Mapping[str, Any]:
        return {"status": "operator_required", "action": "connection_request", "linkedin_url": linkedin_url, "message": message}

    def send_message(self, *, linkedin_url: str, message: str) -> Mapping[str, Any]:
        return {"status": "operator_required", "action": "message", "linkedin_url": linkedin_url, "message": message}

    def observe(self, *, linkedin_url: str) -> Mapping[str, Any]:
        return {"status": "operator_required", "action": "observe", "linkedin_url": linkedin_url}


def validate_sequence(raw_steps: Sequence[Mapping[str, Any]]) -> list[SequenceStep]:
    steps: list[SequenceStep] = []
    for raw in raw_steps:
        steps.append(
            SequenceStep(
                step_no=int(raw["step_no"]),
                action=str(raw["action"]),
                delay_days=int(raw.get("delay_days", 0)),
                message=str(raw["message"]) if raw.get("message") is not None else None,
            )
        )
    steps.sort(key=lambda step: step.step_no)
    expected = list(range(1, len(steps) + 1))
    if [step.step_no for step in steps] != expected:
        raise LinkedInOutreachError("LinkedIn sequence step numbers must be contiguous starting at 1")
    if not steps:
        raise LinkedInOutreachError("LinkedIn sequence must contain at least one step")
    return steps


def build_touchpoints(
    *,
    contact: LinkedInContact,
    sequence_id: str,
    steps: Sequence[SequenceStep],
    start_at: datetime,
) -> list[LinkedInTouchpoint]:
    if start_at.tzinfo is None:
        raise LinkedInOutreachError("start_at must be timezone-aware")
    UUID(sequence_id)
    touchpoints: list[LinkedInTouchpoint] = []
    current = start_at
    for step in steps:
        current += timedelta(days=step.delay_days)
        touchpoints.append(
            LinkedInTouchpoint(
                touchpoint_id=str(uuid4()),
                decision_maker_id=contact.decision_maker_id,
                company_id=contact.company_id,
                channel=LINKEDIN_CHANNEL,
                touchpoint_type=step.action,
                status="planned",
                scheduled_at=current,
                idempotency_key=f"linkedin:{sequence_id}:{contact.decision_maker_id}:{step.step_no}",
                metadata={
                    "sequence_id": sequence_id,
                    "step_no": step.step_no,
                    "linkedin_url": contact.linkedin_url,
                    "recipient_name": contact.full_name,
                    "recipient_title": contact.title,
                    "message": step.message,
                },
            )
        )
    return touchpoints


def next_state_after_observation(
    *,
    current_state: str,
    observation: Mapping[str, Any],
    now: datetime,
    next_action_at: datetime | None,
) -> StateUpdate:
    if now.tzinfo is None:
        raise LinkedInOutreachError("now must be timezone-aware")

    event = str(observation.get("event", "")).strip().lower()
    inbound = bool(observation.get("inbound_message", False))
    connected = observation.get("connected")

    if inbound:
        return StateUpdate("replied", None, "inbound_response_observed")
    if event == "connection_accepted" or connected is True:
        return StateUpdate("active", next_action_at, "connection_acceptance_observed")
    if event == "message_sent":
        return StateUpdate("awaiting_reply", next_action_at, "outbound_message_observed")
    if event == "connection_request_sent":
        return StateUpdate("awaiting_reply", next_action_at, "connection_request_observed")
    if event in {"opt_out", "suppressed"}:
        return StateUpdate("suppressed", None, "explicit_suppression_observed")
    if event == "meeting_booked":
        return StateUpdate("meeting", None, "meeting_booked_observed")
    if event == "closed":
        return StateUpdate("closed", None, "explicit_closed_observed")
    if current_state == "awaiting_reply" and next_action_at is not None and now >= next_action_at:
        return StateUpdate("follow_up_due", next_action_at, "next_action_window_reached_without_inbound_observation")
    return StateUpdate(current_state, next_action_at, "no_state_change")
