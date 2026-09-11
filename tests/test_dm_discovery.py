from sentinellayer_growth_engine.dm_discovery import (
    buyer_roles_for_company,
    discovery_query_plan,
    linkedin_role_queries,
)


def test_small_company_prioritizes_security_technology_and_executive_roles() -> None:
    roles = buyer_roles_for_company(employee_count=40)
    assert [role.key for role in roles] == ["security", "technology", "executive"]


def test_larger_company_expands_to_product_and_operations() -> None:
    roles = buyer_roles_for_company(employee_count=250)
    assert [role.key for role in roles] == ["security", "technology", "executive", "product", "operations"]


def test_large_company_adds_finance_and_procurement() -> None:
    roles = buyer_roles_for_company(employee_count=700)
    assert [role.key for role in roles] == ["security", "technology", "executive", "product", "operations", "finance"]


def test_login_surface_adds_product_without_displacing_security() -> None:
    roles = buyer_roles_for_company(employee_count=40, has_login=True)
    assert [role.key for role in roles] == ["security", "technology", "executive", "product"]


def test_queries_are_narrow_linkedin_public_searches() -> None:
    role = buyer_roles_for_company(employee_count=40)[0]
    queries = linkedin_role_queries(company_label="Example", domain="example.com", role=role)
    assert queries
    assert all('site:linkedin.com/in' in query for query in queries)
    assert any('"CISO"' in query for query in queries)
    assert all('example.com' in query for query in queries)


def test_plan_is_deterministic_and_role_ordered() -> None:
    plan = discovery_query_plan(
        company_label="Example",
        domain="example.com",
        employee_count=250,
    )
    assert [role.key for role, _ in plan] == ["security", "technology", "executive", "product", "operations"]
    assert all(queries for _, queries in plan)
