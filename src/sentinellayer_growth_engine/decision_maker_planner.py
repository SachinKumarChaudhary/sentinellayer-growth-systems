from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BuyerRole:
    family: str
    titles: tuple[str, ...]
    priority: int
    rationale: str


def plan_buyer_roles(
    *,
    employee_count: int | None,
    has_security_leader: bool = False,
    corporate_owned: bool = False,
    subscription: bool = False,
    sensitive_data: bool = False,
    iot: bool = False,
) -> list[BuyerRole]:
    """Translate the existing decision-maker playbook into a deterministic hunt order."""
    roles: list[BuyerRole] = []
    if has_security_leader:
        roles.append(
            BuyerRole(
                "security",
                ("CISO", "Chief Information Security Officer", "Head of Security", "Director of Security", "Security Lead"),
                1,
                "Security leadership overrides company-size ordering.",
            )

    if corporate_owned:
        roles.append(BuyerRole("parent_operator", ("Operating Partner", "Operating Executive", "Portfolio Operations"), 2, "Corporate/PE-owned accounts may route through the parent operating layer."))
        roles.append(BuyerRole("ecommerce", ("Head of Ecommerce", "Ecommerce Director", "VP Ecommerce", "Head of Digital"), 3, "Local ecommerce ownership is the practical operating thread."))
        roles.append(BuyerRole("engineering", ("CTO", "Chief Technology Officer", "VP Engineering", "Head of Engineering", "CIO"), 4, "Engineering can approve the proxy/integration route."))
    elif employee_count is not None and employee_count < 150:
        founder_priority = 2 if has_security_leader else 1
        engineering_priority = 3 if has_security_leader else 2
        roles.append(BuyerRole("founder", ("Founder", "Co-Founder", "CEO", "Chief Executive Officer"), founder_priority, "Smaller companies often concentrate buying authority with founders/executives."))
        roles.append(BuyerRole("engineering", ("CTO", "Chief Technology Officer", "VP Engineering", "Head of Engineering", "CIO"), engineering_priority, "Engineering is the technical approval thread."))
    else:
        engineering_priority = 2 if has_security_leader else 1
        operations_priority = 3 if has_security_leader else 2
        roles.append(BuyerRole("engineering", ("CTO", "Chief Technology Officer", "VP Engineering", "Head of Engineering", "CIO"), engineering_priority, "Mid-market companies need a technical owner for the integration."))
        roles.append(BuyerRole("operations_finance", ("COO", "Chief Operating Officer", "CFO", "Chief Financial Officer", "VP Finance", "Head of Operations"), operations_priority, "Operations/finance provides the economic and operational thread."))

    if subscription:
        roles.append(BuyerRole("payments_finance", ("Head of Payments", "VP Payments", "Payments Director", "CFO", "Head of Finance"), 5, "Recurring billing increases the relevance of payments/finance ownership."))
    if sensitive_data:
        roles.append(BuyerRole("legal", ("General Counsel", "Chief Legal Officer", "Privacy Counsel", "Chief Privacy Officer"), 5, "Sensitive or regulated customer data can create a legal/privacy buying thread."))
    if iot:
        roles.append(BuyerRole("product", ("Chief Product Officer", "VP Product", "Head of Product", "Head of IoT"), 5, "Connected-device accounts make product ownership relevant."))

    unique: dict[str, BuyerRole] = {}
    for role in roles:
        existing = unique.get(role.family)
        if existing is None or role.priority < existing.priority:
            unique[role.family] = role
    return sorted(unique.values(), key=lambda role: (role.priority, role.family))
