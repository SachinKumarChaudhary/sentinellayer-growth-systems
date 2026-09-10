from sentinellayer_growth_engine.decision_maker_planner import plan_buyer_roles


def test_small_company_hunts_founder_then_engineering():
    roles = plan_buyer_roles(employee_count=80)
    assert [r.family for r in roles[:2]] == ["founder", "engineering"]


def test_security_leader_overrides_company_size():
    roles = plan_buyer_roles(employee_count=80, has_security_leader=True)
    assert roles[0].family == "security"


def test_mid_market_pairs_engineering_and_operations_finance():
    roles = plan_buyer_roles(employee_count=300)
    assert [r.family for r in roles[:2]] == ["engineering", "operations_finance"]


def test_contextual_threads_are_added():
    roles = plan_buyer_roles(employee_count=300, subscription=True, sensitive_data=True, iot=True)
    families = {r.family for r in roles}
    assert {"payments_finance", "legal", "product"}.issubset(families)
