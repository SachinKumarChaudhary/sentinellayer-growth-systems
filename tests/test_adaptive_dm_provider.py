from __future__ import annotations

from dataclasses import dataclass

from sentinellayer_growth_engine.adaptive_dm_provider import AdaptiveDecisionMakerProvider
from sentinellayer_growth_engine.enrichment_contracts import CompanyFacts, EnrichmentPacket
from sentinellayer_growth_engine.tinyfish_client import TinyFishSearchResult


@dataclass
class FakeClient:
    queries: list[tuple[str, str]]

    def search(self, query: str, *, purpose: str | None = None) -> list[TinyFishSearchResult]:
        self.queries.append((query, purpose or ""))
        if '"CISO"' in query:
            return [TinyFishSearchResult(
                title="Jane Doe | CISO | Example",
                url="https://www.linkedin.com/in/jane-doe",
                snippet="Jane Doe — CISO at Example",
            )]
        return []


class FakeProvider:
    def __init__(self, client: FakeClient) -> None:
        self._client = client

    def build_packet(self, **_: object) -> EnrichmentPacket:
        return EnrichmentPacket(
            company_id=1,
            domain="example.com",
            merchant_name="Example",
            company_facts=CompanyFacts(employee_count=40, has_login=False),
        )


def test_adaptive_provider_searches_missing_roles_and_stops_alias_fallback_after_match() -> None:
    client = FakeClient(queries=[])
    provider = AdaptiveDecisionMakerProvider(FakeProvider(client))

    packet = provider.build_packet(company_id=1, domain="example.com", merchant_name="Example")

    assert packet.decision_makers
    assert packet.decision_makers[0].full_name == "Jane Doe"
    assert packet.decision_makers[0].role_family == "security"
    security_queries = [query for query, purpose in client.queries if purpose == "decision_maker_role_security"]
    assert len(security_queries) == 1
    assert 'site:linkedin.com/in' in security_queries[0]
    assert '"CISO"' in security_queries[0]


def test_adaptive_provider_keeps_role_budget_bounded_when_no_results() -> None:
    client = FakeClient(queries=[])
    provider = AdaptiveDecisionMakerProvider(FakeProvider(client))

    provider.build_packet(company_id=1, domain="example.com", merchant_name="Example")

    role_queries = [purpose for _, purpose in client.queries if purpose.startswith("decision_maker_role_")]
    assert len(role_queries) == 6
