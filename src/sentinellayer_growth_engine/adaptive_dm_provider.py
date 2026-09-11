from __future__ import annotations

from datetime import UTC, datetime

from .decision_maker_pipeline import ResolvedTinyFishProvider, resolve_decision_makers
from .dm_discovery import discovery_query_plan
from .enrichment_contracts import DecisionMaker, EnrichmentPacket
from .tinyfish_enrichment import TinyFishEnrichmentProvider


def _role_key_for_candidate(dm: DecisionMaker) -> str | None:
    """Map an existing candidate's role/title to the discovery planner family."""
    if dm.role_family:
        return dm.role_family.strip().lower()
    title = (dm.title or "").casefold()
    if not title:
        return None
    role_aliases = {
        "security": ("ciso", "chief information security officer", "head of security", "vp security"),
        "technology": ("cto", "chief technology officer", "vp engineering", "head of engineering", "vp technology"),
        "executive": ("ceo", "chief executive officer", "founder", "co-founder", "president"),
        "product": ("cpo", "chief product officer", "vp product", "head of product"),
        "operations": ("coo", "chief operating officer", "vp operations", "head of operations"),
        "finance": ("cfo", "chief financial officer", "vp finance", "procurement", "head of procurement"),
    }
    for role_key, aliases in role_aliases.items():
        if any(alias in title for alias in aliases):
            return role_key
    return None


class AdaptiveDecisionMakerProvider(ResolvedTinyFishProvider):
    """Add narrow role searches only for buyer roles still missing after baseline research."""

    def build_packet(self, **kwargs: object) -> EnrichmentPacket:
        packet = self._provider.build_packet(**kwargs)  # type: ignore[attr-defined]
        if not isinstance(packet, EnrichmentPacket):
            raise TypeError("TinyFish provider returned an invalid enrichment packet")

        employee_count = packet.company_facts.employee_count
        has_login = packet.company_facts.has_login
        company_label = packet.merchant_name or packet.domain
        plan = discovery_query_plan(
            company_label=company_label,
            domain=packet.domain,
            employee_count=employee_count,
            has_login=has_login,
        )
        existing_roles = {
            role_key
            for dm in packet.decision_makers
            if (role_key := _role_key_for_candidate(dm)) is not None
        }
        client = getattr(self._provider, "_client", None)
        if client is None:
            return resolve_decision_makers(packet)

        for role, queries in plan:
            if role.key in existing_roles:
                continue
            for alias_index, query in enumerate(queries[:2]):
                results = client.search(
                    query,
                    purpose=f"decision_maker_role_{role.key}",
                )
                TinyFishEnrichmentProvider._augment_decision_makers_from_search(
                    packet,
                    [(f"decision_maker_role_{role.key}", results)],
                    packet.domain,
                    company_label,
                    datetime.now(UTC),
                )
                existing_roles = {
                    role_key
                    for dm in packet.decision_makers
                    if (role_key := _role_key_for_candidate(dm)) is not None
                }
                if role.key in existing_roles or alias_index == 1:
                    break

        return resolve_decision_makers(packet)
