from sentinellayer_growth_engine.decision_maker_ranking import rank_decision_makers
from sentinellayer_growth_engine.enrichment_contracts import ContactMethod, DecisionMaker


def _dm(name: str, title: str, family: str, priority: int, status: str = "unknown") -> DecisionMaker:
    return DecisionMaker(
        full_name=name,
        title=title,
        role_family=family,
        role_priority=priority,
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


def test_ranking_prefers_security_and_verified_contacts() -> None:
    ranked = rank_decision_makers(
        [
            _dm("Product Lead", "Product Lead", "product", 3),
            _dm("Security VP", "VP Security", "security", 2, "verified"),
            _dm("Engineering Director", "Engineering Director", "engineering", 1),
        ]
    )
    assert [item.decision_maker.full_name for item in ranked] == [
        "Security VP",
        "Engineering Director",
        "Product Lead",
    ]
    assert ranked[0].eligible is True
    assert ranked[0].score > ranked[1].score


def test_ciso_is_suppressed_and_never_ranked_as_eligible() -> None:
    ranked = rank_decision_makers(
        [
            _dm("CISO", "CISO", "security", 1, "verified"),
            _dm("Identity Head", "Head of Identity", "identity", 2, "verified"),
        ]
    )
    assert ranked[0].decision_maker.full_name == "Identity Head"
    ciso = next(item for item in ranked if item.decision_maker.full_name == "CISO")
    assert ciso.eligible is False
    assert ciso.reason == "ciso_suppressed_by_policy"


def test_limit_keeps_operator_queue_bounded() -> None:
    ranked = rank_decision_makers(
        [_dm(f"Person {index}", "Director Product", "product", index) for index in range(1, 8)],
        limit=3,
    )
    assert len(ranked) == 3
