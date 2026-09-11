from __future__ import annotations

from datetime import UTC, datetime

from .decision_maker_pipeline import ResolvedTinyFishProvider
from .dm_discovery import discovery_query_plan
from .enrichment_contracts import EnrichmentPacket
from .tinyfish_enrichment import TinyFishEnrichmentProvider


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
        existing_roles = {dm.role_family for dm in packet.decision_makers if dm.role_family}
        client = getattr(self._provider, "_client", None)
        if client is None:
            return packet

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
                existing_roles = {dm.role_family for dm in packet.decision_makers if dm.role_family}
                if role.key in existing_roles or alias_index == 1:
                    break

        return packet
