from sentinellayer_growth_engine.recommendations import recommend_next_action


def test_p1_can_use_optional_social_warming() -> None:
    result = recommend_next_action(
        priority="P1",
        has_conversation=False,
        awaiting_reply=False,
        available_channels=("email", "linkedin"),
        social_warming_available=True,
    )
    assert result.recommended_channel == "social_content"
    assert result.requires_approval is True


def test_active_conversation_keeps_followup_in_conversation() -> None:
    result = recommend_next_action(
        priority="P1",
        has_conversation=True,
        awaiting_reply=False,
        available_channels=("email", "linkedin"),
        social_warming_available=False,
    )
    assert result.recommendation_type == "conversation_followup"
    assert result.recommended_channel == "email"


def test_no_automation_becomes_operator_action() -> None:
    result = recommend_next_action(
        priority="P2",
        has_conversation=False,
        awaiting_reply=False,
        available_channels=(),
        social_warming_available=False,
    )
    assert result.recommended_channel == "none"
    assert result.recommendation_type == "operator_action"
