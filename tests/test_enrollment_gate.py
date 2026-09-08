from datetime import UTC, datetime

import pytest

from sentinellayer_growth_engine.contact_verification import VerificationOrchestrator
from sentinellayer_growth_engine.decision_maker_ranking import rank_decision_makers
from sentinellayer_growth_engine.enrichment_contracts import ContactMethod, DecisionMaker
from sentinellayer_growth_engine.enrollment_gate import (
    EnrollmentGateError,
    OperatorApproval,
    validate_enrollment_gate,
)


def _dm(name: str, title: str, family: str, status: str = "unknown") -> DecisionMaker:
    return DecisionMaker(
        full_name=name,
        title=title,
        role_family=family,
        role_priority=1,
        confidence=0.9,
        contacts=[
            ContactMethod(
                channel="email",
                value=f"{name.lower().replace(' ', '.')}@example.com",
                normalized_value=f"{name.lower().replace(' ', '.')}@example.com",
                verification_status=status,
            )
        ],
    )


def test_verified_contact_is_required_for_enrollment() -> None:
    ranked = rank_decision_makers([_dm("Security VP", "VP Security", "security")])[0]
    with pytest.raises(EnrollmentGateError, match="verified contact"):
        validate_enrollment_gate(ranked, OperatorApproval("operator-1", datetime.now(UTC)))


def test_operator_approval_is_required_after_verification() -> None:
    ranked = rank_decision_makers([_dm("Security VP", "VP Security", "security", "verified")])[0]
    with pytest.raises(EnrollmentGateError, match="operator approval"):
        validate_enrollment_gate(ranked, None)


def test_denied_approval_cannot_enroll() -> None:
    ranked = rank_decision_makers([_dm("Security VP", "VP Security", "security", "verified")])[0]
    approval = OperatorApproval("operator-1", datetime.now(UTC), approved=False)
    with pytest.raises(EnrollmentGateError, match="denied"):
        validate_enrollment_gate(ranked, approval)


def test_ciso_suppression_survives_gate() -> None:
    ranked = rank_decision_makers([_dm("CISO", "CISO", "security", "verified")])[0]
    with pytest.raises(EnrollmentGateError, match="not eligible"):
        validate_enrollment_gate(
            ranked,
            OperatorApproval("operator-1", datetime.now(UTC)),
        )


def test_verified_and_approved_contact_can_enroll() -> None:
    ranked = rank_decision_makers([_dm("Security VP", "VP Security", "security", "verified")])[0]
    result = validate_enrollment_gate(
        ranked,
        OperatorApproval("operator-1", datetime.now(UTC)),
    )
    assert result.decision_maker_name == "Security VP"
    assert result.verification_status == "verified"
    assert result.operator_id == "operator-1"


def test_verification_orchestrator_without_provider_does_not_upgrade_status() -> None:
    contact = _dm("Security VP", "VP Security", "security").contacts[0]
    result = VerificationOrchestrator([]).verify(contact)
    assert result.status == "unknown"
