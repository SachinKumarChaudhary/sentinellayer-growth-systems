from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .enrichment_contracts import EnrichmentBatch, EnrichmentPacket
from .enrichment_repository import EnrichmentRepository
from .tinyfish_enrichment import TinyFishEnrichmentProvider


@dataclass(frozen=True)
class CompanySeed:
    company_id: int
    domain: str
    merchant_name: str | None


class CompanySeedRepository(Protocol):
    def next_companies(self, limit: int = 3) -> list[int]:
        ...

    def company_seed(self, company_id: int) -> CompanySeed:
        ...


class TinyFishBatchEnricher:
    """Run the bounded TinyFish research pipeline for the next 1-3 companies."""

    def __init__(
        self,
        repository: EnrichmentRepository,
        provider: TinyFishEnrichmentProvider,
    ) -> None:
        self._repository = repository
        self._provider = provider

    def build_next_batch(self, *, limit: int = 3) -> EnrichmentBatch:
        company_ids = self._repository.next_companies(limit=limit)
        packets: list[EnrichmentPacket] = []
        for company_id in company_ids:
            seed = self._repository.company_seed(company_id)
            packets.append(
                self._provider.build_packet(
                    company_id=seed.company_id,
                    domain=seed.domain,
                    merchant_name=seed.merchant_name,
                )
            )
        return EnrichmentBatch(packets=packets)

    def run_next(self, *, limit: int = 3, persist: bool = True) -> dict[str, object]:
        batch = self.build_next_batch(limit=limit)
        if not persist:
            return {
                "provider": "tinyfish",
                "persisted": False,
                "batch": batch.model_dump(mode="json"),
            }
        result = self._repository.persist_batch(batch, provider="tinyfish")
        return {"provider": "tinyfish", "persisted": True, "result": result}
