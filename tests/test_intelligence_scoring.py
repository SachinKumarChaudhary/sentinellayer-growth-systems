from datetime import date

from sentinellayer_growth_engine.intelligence_scoring import IntentSignalInput, score_company


def test_high_fit_and_fresh_intent_routes_p1() -> None:
    result = score_company(
        employee_count=180,
        monthly_sessions=900_000,
        has_login=True,
        notes="IoT app-connected device, subscription, SOC 2",
        signals=[
            IntentSignalInput("funding", date(2026, 9, 1), 3, 21),
            IntentSignalInput("security_hiring", date(2026, 9, 5), 2, 30),
        ],
        today=date(2026, 9, 8),
    )
    assert result.fit_score > 5
    assert result.intent_score > 5
    assert result.priority == "P1"


def test_corporate_route_caps_priority_at_p3() -> None:
    result = score_company(
        employee_count=200,
        monthly_sessions=1_000_000,
        has_login=True,
        notes="parent-owned decisions centralized",
        signals=[IntentSignalInput("funding", date(2026, 9, 7), 3, 21)],
        today=date(2026, 9, 8),
    )
    assert result.priority == "P3"


def test_behavior_override_forces_p1() -> None:
    result = score_company(
        employee_count=60,
        monthly_sessions=150_000,
        has_login=True,
        notes="ordinary DTC",
        signals=[],
        today=date(2026, 9, 8),
        behavior_override=True,
    )
    assert result.priority == "P1"
    assert "behavior_override" in result.modifiers


def test_india_bridge_can_promote_one_tier() -> None:
    result = score_company(
        employee_count=100,
        monthly_sessions=200_000,
        has_login=True,
        notes="ordinary DTC",
        signals=[],
        today=date(2026, 9, 8),
        india_bridge=True,
    )
    assert result.priority == "P3"
