from sentinellayer_growth_engine.conversation_policy import reconcile_conversation_analysis


def test_unsubscribe_cannot_be_overridden_by_positive_model_intent() -> None:
    result = reconcile_conversation_analysis(
        deterministic_classification="unsubscribe",
        analysis={
            "primary_intent": "interested",
            "secondary_intents": [],
            "objections": [],
            "explicit_opt_out": False,
        },
    )
    assert result["send_allowed"] is False
    assert result["action"] == "suppress_contact"


def test_negative_cannot_be_overridden_by_model_interest() -> None:
    result = reconcile_conversation_analysis(
        deterministic_classification="negative",
        analysis={"primary_intent": "interested", "explicit_opt_out": False},
    )
    assert result["send_allowed"] is False
    assert result["action"] == "stop_cold_sequence"


def test_not_now_cannot_be_promoted_to_immediate_follow_up() -> None:
    result = reconcile_conversation_analysis(
        deterministic_classification="not_now",
        analysis={"primary_intent": "interested", "explicit_opt_out": False},
    )
    assert result["send_allowed"] is False
    assert result["action"] == "schedule_later"


def test_semantic_opt_out_is_safe_even_when_regex_missed_it() -> None:
    result = reconcile_conversation_analysis(
        deterministic_classification="other",
        analysis={"primary_intent": "other", "explicit_opt_out": True},
    )
    assert result["send_allowed"] is False
    assert result["action"] == "suppress_contact"


def test_interested_can_be_enriched_by_semantic_analysis() -> None:
    result = reconcile_conversation_analysis(
        deterministic_classification="interested",
        analysis={"primary_intent": "objection", "explicit_opt_out": False},
    )
    assert result["send_allowed"] is True
    assert result["action"] == "human_follow_up"
