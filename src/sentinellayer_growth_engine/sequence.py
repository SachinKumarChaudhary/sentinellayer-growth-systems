from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from .resolver import CampaignResolutionError, select_sequence_step

TERMINAL_STATUSES = frozenset({"replied", "completed", "suppressed", "bounced", "cancelled"})


class SequenceOrchestrationError(RuntimeError):
    """Raised when sequence progression cannot be safely determined."""


@dataclass(frozen=True)
class SequenceAction:
    enrollment_id: str
    sequence_version_id: str
    step: Mapping[str, Any]
    scheduled_at: datetime


@dataclass(frozen=True)
class EnrollmentState:
    enrollment_id: str
    sequence_version_id: str
    current_step_no: int
    status: str
    next_action_at: datetime | None


class SequenceOrchestrator:
    """Select the next campaign step; it never sends mail.

    Persistence and delivery remain outside this component. The caller must
    atomically persist progression and hand the resulting treatment to Mail.
    """

    def next_action(
        self,
        *,
        enrollment: EnrollmentState,
        sequence_steps: Sequence[Mapping[str, Any]],
        now: datetime,
        max_steps: int,
    ) -> SequenceAction | None:
        if enrollment.status in TERMINAL_STATUSES:
            return None
        if max_steps < 1:
            raise SequenceOrchestrationError("max_steps must be positive")
        if enrollment.current_step_no >= max_steps:
            return None
        if enrollment.next_action_at is not None and enrollment.next_action_at > now:
            return None

        step_no = enrollment.current_step_no + 1
        try:
            step = select_sequence_step(
                sequence_steps=sequence_steps,
                sequence_version_id=enrollment.sequence_version_id,
                step_no=step_no,
            )
        except (CampaignResolutionError, ValueError, TypeError) as exc:
            raise SequenceOrchestrationError(str(exc)) from exc

        try:
            delay_days = int(step.get("delay_days", 0))
        except (TypeError, ValueError) as exc:
            raise SequenceOrchestrationError("sequence step has invalid delay_days") from exc
        if delay_days < 0:
            raise SequenceOrchestrationError("sequence step delay_days cannot be negative")

        return SequenceAction(
            enrollment_id=enrollment.enrollment_id,
            sequence_version_id=enrollment.sequence_version_id,
            step=step,
            scheduled_at=now + timedelta(days=delay_days),
        )
