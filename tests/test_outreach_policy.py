from sentinellayer_growth_engine.outreach_policy import evaluate_decision_maker


def test_ciso_is_suppressed() -> None:
    result = evaluate_decision_maker(title="CISO")
    assert result.eligible is False
    assert result.reason == "ciso_suppressed_by_policy"


def test_other_decision_makers_require_human_review() -> None:
    result = evaluate_decision_maker(title="VP Engineering")
    assert result.eligible is True
    assert result.requires_human_approval is True
