from datetime import date

from sentinellayer_growth_engine.intelligence_scoring import (
    IntentSignalInput,
    compute_intent,
    score_company,
)


TODAY = date(2026, 9, 8)


def high_fit_notes() -> str:
    return "IoT app-connected device, subscription, kids minors, health data, SOC 2"


def test_high_fit_and_fresh_intent_routes_p1() -> None:
    result = score_company(
        employee_count=180,
        monthly_sessions=900_000,
        has_login=True,
        notes=high_fit_notes(),
        signals=[
            IntentSignalInput("funding", date(2026, 9, 1), 3, 21),
            IntentSignalInput("security_hiring", date(2026, 9, 5), 3, 30),
            IntentSignalInput("explicit_incident", date(2026, 9, 7), 4, 14),
        ],
        today=TODAY,
    )
    assert result.fit_score > 5
    assert result.intent_score > 5
    assert result.priority == "P1"
    assert result.raw_intent == sum(component.value for component in result.intent_components)


def test_negative_flags_do_not_reduce_fit_but_apply_routing_cap() -> None:
    baseline = score_company(
        employee_count=200,
        monthly_sessions=1_000_000,
        has_login=True,
        notes=high_fit_notes(),
        signals=[IntentSignalInput("funding", date(2026, 9, 7), 3, 21)],
        today=TODAY,
    )
    corporate = score_company(
        employee_count=200,
        monthly_sessions=1_000_000,
        has_login=True,
        notes=high_fit_notes() + " parent-owned decisions centralized",
        signals=[IntentSignalInput("funding", date(2026, 9, 7), 3, 21)],
        today=TODAY,
    )
    assert corporate.fit_score == baseline.fit_score
    assert corporate.priority == "P3"
    assert "corporate_route_only" in corporate.negative_flags


def test_ma_freeze_caps_p1_at_p2() -> None:
    result = score_company(
        employee_count=180,
        monthly_sessions=900_000,
        has_login=True,
        notes=high_fit_notes() + " recently acquired post-acquisition integration",
        signals=[
            IntentSignalInput("explicit_incident", date(2026, 9, 7), 4, 14),
            IntentSignalInput("security_hiring", date(2026, 9, 8), 3, 30),
        ],
        today=TODAY,
    )
    assert result.intent_score > 5
    assert result.priority == "P2"
    assert "ma_freeze_cap" in result.modifiers


def test_duplicate_events_do_not_inflate_intent() -> None:
    signal = IntentSignalInput("security_hiring", date(2026, 9, 7), 3, 30, dedupe_key="job-123")
    score, raw, components = compute_intent(signals=[signal, signal], today=TODAY)
    assert score == 3.0
    assert raw == 3.0
    assert len(components) == 1


def test_evergreen_compliance_context_is_not_buying_intent() -> None:
    score, raw, components = compute_intent(
        signals=[
            IntentSignalInput("pci", date(2026, 9, 8), 3, 9999),
            IntentSignalInput("gdpr", date(2026, 9, 8), 2, 9999),
        ],
        today=TODAY,
    )
    assert score == 0.0
    assert raw == 0.0
    assert components == ()


def test_anonymous_docs_research_does_not_force_p1() -> None:
    result = score_company(
        employee_count=200,
        monthly_sessions=1_000_000,
        has_login=True,
        notes="ordinary DTC",
        signals=[IntentSignalInput("docs_visit", TODAY, 4, 7)],
        today=TODAY,
    )
    assert result.intent_score == 4.0
    assert result.priority == "P2"


def test_identified_technical_evaluation_forces_p1() -> None:
    result = score_company(
        employee_count=60,
        monthly_sessions=150_000,
        has_login=True,
        notes="ordinary DTC",
        signals=[],
        today=TODAY,
        behavior_stage="IDENTIFIED_TECHNICAL_EVALUATION",
    )
    assert result.priority == "P1"
    assert result.behavior_override
    assert "behavior_p1" in result.modifiers


def test_india_bridge_promotes_one_tier_but_cannot_override_corporate_cap() -> None:
    result = score_company(
        employee_count=100,
        monthly_sessions=200_000,
        has_login=True,
        notes=high_fit_notes() + " parent-owned decisions centralized",
        signals=[],
        today=TODAY,
        india_bridge=True,
    )
    assert result.priority == "P3"


def test_decision_maker_depth_is_routing_metadata_not_intent() -> None:
    result = score_company(
        employee_count=100,
        monthly_sessions=200_000,
        has_login=True,
        notes=high_fit_notes(),
        signals=[],
        today=TODAY,
        decision_maker_depth=2,
    )
    assert result.intent_score == 0.0
    assert "decision_maker_depth" in result.modifiers
