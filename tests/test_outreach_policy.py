from sentinellayer_growth_engine.outreach_policy import (
    evaluate_contact_for_outreach,
    evaluate_decision_maker,
)


def test_ciso_is_suppressed() -> None:
    result = evaluate_decision_maker(title="CISO")
    assert result.eligible is False
    assert result.reason == "ciso_suppressed_by_policy"


def test_other_decision_makers_require_human_review() -> None:
    result = evaluate_decision_maker(title="VP Engineering")
    assert result.eligible is True
    assert result.requires_human_approval is True


def test_unverified_contact_cannot_be_approved_for_outreach() -> None:
    result = evaluate_contact_for_outreach(
        title="VP Engineering",
        verification_status="candidate",
    )
    assert result.eligible is False
    assert result.reason == "contact_not_verified"


def test_verified_contact_remains_human_reviewed() -> None:
    result = evaluate_contact_for_outreach(
        title="VP Engineering",
        verification_status="verified",
    )
    assert result.eligible is True
    assert result.requires_human_approval is True
