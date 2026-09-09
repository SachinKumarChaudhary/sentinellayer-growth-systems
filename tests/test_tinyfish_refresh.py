from dataclasses import dataclass

from sentinellayer_growth_engine.enrichment_contracts import CompanyFacts, EnrichmentBatch, EnrichmentPacket
from sentinellayer_growth_engine.tinyfish_batch import CompanySeed, TinyFishRefreshEnricher


@dataclass
class FakeRepository:
    ids: list[int]
    persisted: list[EnrichmentBatch]

    def next_companies(self, limit: int = 3) -> list[int]:
        return self.ids[:limit]

    def next_enrichment_company_ids(self, limit: int = 40) -> list[int]:
        return []

    def next_refresh_company_ids(self, limit: int = 10, min_age_days: int = 7) -> list[int]:
        assert min_age_days == 7
        return self.ids[:limit]

    def persist_batch(self, batch: EnrichmentBatch, *, provider: str = "manual_ai_research"):
        assert provider == "tinyfish_refresh"
        self.persisted.append(batch)
        return {"provider": provider, "results": []}


@dataclass
class FakeResolver:
    seeds: dict[int, CompanySeed]

    def resolve(self, company_id: int) -> CompanySeed:
        return self.seeds[company_id]


@dataclass
class FakeProvider:
    calls: list[tuple[int, int]]

    def build_packet(self, *, company_id: int, domain: str, merchant_name: str | None = None, max_fetch_urls: int = 10):
        self.calls.append((company_id, max_fetch_urls))
        return EnrichmentPacket(
            company_id=company_id,
            domain=domain,
            merchant_name=merchant_name,
            company_facts=CompanyFacts(has_login=True),
            company_contacts=[],
            decision_makers=[],
            intent_signals=[],
            personalization_angle=None,
            research_notes=["refresh test"],
        )


def test_refresh_runner_is_bounded_and_uses_smaller_fetch_budget() -> None:
    ids = [11, 12, 13]
    repository = FakeRepository(ids=ids, persisted=[])
    resolver = FakeResolver({i: CompanySeed(i, f"company{i}.example", None) for i in ids})
    provider = FakeProvider(calls=[])
    runner = TinyFishRefreshEnricher(repository, provider, resolver)

    result = runner.run_refresh(limit=3, min_age_days=7)

    assert result.requested == 3
    assert result.succeeded == 3
    assert result.failed == 0
    assert provider.calls == [(11, 8), (12, 8), (13, 8)]
    assert len(repository.persisted) == 3
