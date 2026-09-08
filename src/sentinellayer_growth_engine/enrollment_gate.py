from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .decision_maker_ranking import RankedDecisionMaker


class EnrollmentGateError(ValueError):
    """Raised when a ranked decision maker cannot enter campaign enrollment."""


@dataclass(frozen=True)
class OperatorApproval:
    operator_id: str
    approved_at: datetime
    approved: bool = True


@dataclass(frozen=True)
class EnrollmentGateResult:
    decision_maker_name: str
    ranking_score: float
    verification_status: str
    operator_id: str
    approved_at: datetime


def _verified_contact_exists(ranked: RankedDecisionMaker) -> bool:
    return any(contact.verification_status == "verified" for contact in ranked.decision_maker.contacts)


def validate_enrollment_gate(
    ranked: RankedDecisionMaker,
    approval: OperatorApproval | None,
) -> EnrollmentGateResult:
    """Require ranking eligibility, verified contact data, and explicit human approval."""
    if not ranked.eligible:
        raise EnrollmentGateError(f"decision maker is not eligible: {ranked.reason}")
    if not _verified_contact_exists(ranked):
        raise EnrollmentGateError("enrollment requires at least one verified contact")
    if approval is None:
        raise EnrollmentGateError("operator approval is required before enrollment")
    if not approval.approved:
        raise EnrollmentGateError("operator approval was denied")
    if not approval.operator_id.strip():
        raise EnrollmentGateError("operator_id is required for approval")
    if approval.approved_at.tzinfo is None:
        raise EnrollmentGateError("approved_at must be timezone-aware")

    return EnrollmentGateResult(
        decision_maker_name=ranked.decision_maker.full_name,
        ranking_score=ranked.score,
        verification_status="verified",
        operator_id=approval.operator_id,
        approved_at=approval.approved_at,
    )
