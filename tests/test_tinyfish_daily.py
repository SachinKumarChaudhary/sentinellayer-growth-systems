from dataclasses import dataclass

from sentinellayer_growth_engine.enrichment_contracts import CompanyFacts, EnrichmentBatch, EnrichmentPacket
from sentinellayer_growth_engine.tinyfish_batch import CompanySeed, TinyFishDailyEnricher


@dataclass
class FakeRepository:
    ids: list[int]
    persisted: list[EnrichmentBatch]

    def next_companies(self, limit: int = 3) -> list[int]:
        return self.ids[:limit]

    def next_enrichment_company_ids(self, limit: int = 40) -> list[int]:
        return self.ids[:limit]

    def next_refresh_company_ids(self, limit: int = 10, min_age_days: int = 7) -> list[int]:
        return []

    def persist_batch(self, batch: EnrichmentBatch, *, provider: str = "manual_ai_research"):
        assert provider == "tinyfish"
        self.persisted.append(batch)
        return {"provider": provider, "results": []}


@dataclass
class FakeResolver:
    seeds: dict[int, CompanySeed]

    def resolve(self, company_id: int) -> CompanySeed:
        return self.seeds[company_id]


@dataclass
class FakeProvider:
    calls: list[int]
    fail_ids: set[int]

    def build_packet(self, *, company_id: int, domain: str, merchant_name: str | None = None, max_fetch_urls: int = 10):
        self.calls.append(company_id)
        if company_id in self.fail_ids:
            raise RuntimeError("research failed")
        return EnrichmentPacket(
            company_id=company_id,
            domain=domain,
            merchant_name=merchant_name,
            company_facts=CompanyFacts(has_login=True),
            company_contacts=[],
            decision_makers=[],
            intent_signals=[],
            personalization_angle=None,
            research_notes=["test"],
        )


def _runner(fail_ids: set[int] | None = None):
    ids = [2, 3, 4]
    repository = FakeRepository(ids=ids, persisted=[])
    resolver = FakeResolver(seeds={i: CompanySeed(i, f"company{i}.example", f"Company {i}") for i in ids})
    provider = FakeProvider(calls=[], fail_ids=fail_ids or set())
    return TinyFishDailyEnricher(repository, provider, resolver), repository, provider


def test_daily_runner_persists_each_successful_company_independently():
    runner, repository, provider = _runner({3})

    result = runner.run_daily(limit=3)

    assert result.requested == 3
    assert result.succeeded == 2
    assert result.failed == 1
    assert provider.calls == [2, 3, 4]
    assert len(repository.persisted) == 2
    assert [batch.packets[0].company_id for batch in repository.persisted] == [2, 4]
    assert result.failures == [{"company_id": 3, "error": "research failed"}]


def test_daily_runner_stops_at_forty_company_contract():
    runner, repository, _ = _runner()

    result = runner.run_daily(limit=3)

    assert result.requested == 3
    assert len(repository.persisted) == 3
