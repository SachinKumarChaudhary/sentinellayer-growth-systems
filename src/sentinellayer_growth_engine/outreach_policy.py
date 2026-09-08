from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


VerificationStatus = Literal["verified", "invalid", "stale", "unknown", "candidate"]


@dataclass(frozen=True)
class OutreachEligibility:
    eligible: bool
    reason: str
    requires_human_approval: bool


def evaluate_decision_maker(*, title: str | None, explicitly_suppressed: bool = False) -> OutreachEligibility:
    """Apply the current policy: CISO is suppressed; other decisions remain human-reviewed."""
    normalized = (title or "").strip().lower()
    if explicitly_suppressed:
        return OutreachEligibility(False, "explicit_suppression", True)

    ciso_titles = {
        "ciso",
        "chief information security officer",
        "chief information security & risk officer",
        "chief information security and risk officer",
    }
    if normalized in ciso_titles:
        return OutreachEligibility(False, "ciso_suppressed_by_policy", True)

    return OutreachEligibility(True, "eligible_for_human_review", True)


def evaluate_contact_for_outreach(
    *,
    title: str | None,
    verification_status: VerificationStatus,
    explicitly_suppressed: bool = False,
) -> OutreachEligibility:
    """Require a verified contact before an outreach action can be approved."""
    decision = evaluate_decision_maker(title=title, explicitly_suppressed=explicitly_suppressed)
    if not decision.eligible:
        return decision
    if verification_status == "verified":
        return decision
    if verification_status == "invalid":
        return OutreachEligibility(False, "contact_invalid", True)
    if verification_status == "stale":
        return OutreachEligibility(False, "contact_verification_stale", True)
    return OutreachEligibility(False, "contact_not_verified", True)
