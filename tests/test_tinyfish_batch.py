from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sentinellayer_growth_engine.enrichment_contracts import (
    CompanyFacts,
    EnrichmentBatch,
    EnrichmentPacket,
)
from sentinellayer_growth_engine.tinyfish_batch import (
    CompanySeed,
    TinyFishBatchEnricher,
)


@dataclass
class FakeRepository:
    ids: list[int]
    persisted: list[tuple[EnrichmentBatch, str]]

    def next_companies(self, limit: int = 3) -> list[int]:
        assert 1 <= limit <= 3
        return self.ids[:limit]

    def persist_batch(self, batch: EnrichmentBatch, *, provider: str) -> dict[str, Any]:
        self.persisted.append((batch, provider))
        return {"provider": provider, "results": []}


@dataclass
class FakeResolver:
    seeds: dict[int, CompanySeed]

    def resolve(self, company_id: int) -> CompanySeed:
        return self.seeds[company_id]


@dataclass
class FakeProvider:
    calls: list[tuple[int, str, str | None]]

    def build_packet(
        self,
        *,
        company_id: int,
        domain: str,
        merchant_name: str | None = None,
    ) -> EnrichmentPacket:
        self.calls.append((company_id, domain, merchant_name))
        return EnrichmentPacket(
            company_id=company_id,
            domain=domain,
            merchant_name=merchant_name,
            company_facts=CompanyFacts(has_login=True),
            company_contacts=[],
            decision_makers=[],
            intent_signals=[],
            personalization_angle=None,
            research_notes=["fake evidence"],
        )


def _enricher() -> tuple[TinyFishBatchEnricher, FakeRepository, FakeResolver, FakeProvider]:
    repository = FakeRepository(ids=[2, 3, 4], persisted=[])
    resolver = FakeResolver(
        seeds={
            2: CompanySeed(2, "byrna.com", "Byrna"),
            3: CompanySeed(3, "atari.com", "Atari®"),
            4: CompanySeed(4, "citywinery.com", "City Winery"),
        }
    )
    provider = FakeProvider(calls=[])
    return TinyFishBatchEnricher(repository, provider, resolver), repository, resolver, provider


def test_build_next_batch_is_bounded_and_uses_canonical_company_identity() -> None:
    enricher, _, _, provider = _enricher()

    batch = enricher.build_next_batch(limit=3)

    assert [packet.company_id for packet in batch.packets] == [2, 3, 4]
    assert provider.calls == [
        (2, "byrna.com", "Byrna"),
        (3, "atari.com", "Atari®"),
        (4, "citywinery.com", "City Winery"),
    ]


def test_run_next_dry_run_does_not_persist() -> None:
    enricher, repository, _, _ = _enricher()

    result = enricher.run_next(limit=2, persist=False)

    assert result["persisted"] is False
    assert repository.persisted == []
    assert len(result["batch"]["packets"]) == 2  # type: ignore[index]


def test_run_next_persists_only_after_batch_build_succeeds() -> None:
    enricher, repository, _, _ = _enricher()

    result = enricher.run_next(limit=3, persist=True)

    assert result["persisted"] is True
    assert len(repository.persisted) == 1
    assert repository.persisted[0][1] == "tinyfish"
    assert [p.company_id for p in repository.persisted[0][0].packets] == [2, 3, 4]
