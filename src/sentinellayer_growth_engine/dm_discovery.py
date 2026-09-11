from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BuyerRole:
    key: str
    aliases: tuple[str, ...]
    priority: int


BUYER_ROLES: tuple[BuyerRole, ...] = (
    BuyerRole("security", ("CISO", "Chief Information Security Officer", "Head of Security", "VP Security", "Security"), 1),
    BuyerRole("technology", ("CTO", "Chief Technology Officer", "VP Engineering", "Head of Engineering", "VP Technology"), 2),
    BuyerRole("executive", ("CEO", "Chief Executive Officer", "Founder", "Co-Founder", "President"), 3),
    BuyerRole("product", ("CPO", "Chief Product Officer", "VP Product", "Head of Product", "Product"), 4),
    BuyerRole("operations", ("COO", "Chief Operating Officer", "VP Operations", "Head of Operations"), 5),
    BuyerRole("finance", ("CFO", "Chief Financial Officer", "VP Finance", "Procurement", "Head of Procurement"), 6),
)


def normalize_company_label(value: str) -> str:
    return " ".join(value.split()).strip()


def buyer_roles_for_company(*, employee_count: int | None, has_login: bool | None = None) -> tuple[BuyerRole, ...]:
    """Return a precision-first role set; company size controls breadth."""
    roles = list(BUYER_ROLES[:3])
    if employee_count is not None:
        if employee_count >= 200:
            roles.append(BUYER_ROLES[3])
        if employee_count >= 500:
            roles.extend(BUYER_ROLES[4:6])
        elif employee_count >= 100:
            roles.append(BUYER_ROLES[4])
    if has_login:
        # Product/technology are useful for account/authentication surfaces, but
        # do not displace security or executive roles.
        if BUYER_ROLES[3] not in roles:
            roles.append(BUYER_ROLES[3])
    return tuple(sorted(set(roles), key=lambda role: role.priority))


def linkedin_role_queries(*, company_label: str, domain: str, role: BuyerRole) -> tuple[str, ...]:
    """Build narrow public-search queries. LinkedIn URLs remain candidate evidence."""
    company = normalize_company_label(company_label) or domain.strip()
    clean_domain = domain.strip().removeprefix("https://").removeprefix("http://").rstrip("/")
    queries: list[str] = []
    for alias in role.aliases:
        queries.append(
            f'"{company}" "{alias}" {clean_domain} site:linkedin.com/in'
        )
    return tuple(queries)


def discovery_query_plan(
    *,
    company_label: str,
    domain: str,
    employee_count: int | None,
    has_login: bool | None = None,
) -> tuple[tuple[BuyerRole, tuple[str, ...]], ...]:
    """Return deterministic role-specific public search queries."""
    return tuple(
        (role, linkedin_role_queries(company_label=company_label, domain=domain, role=role))
        for role in buyer_roles_for_company(employee_count=employee_count, has_login=has_login)
    )
