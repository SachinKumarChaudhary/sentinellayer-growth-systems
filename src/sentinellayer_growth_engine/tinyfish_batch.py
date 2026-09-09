from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .enrichment_contracts import EnrichmentBatch, EnrichmentPacket


@dataclass(frozen=True)
class CompanySeed:
    company_id: int
    domain: str
    merchant_name: str | None


class ConnectionFactory(Protocol):
    def __call__(self) -> Any:
        ...


class CompanySeedResolver(Protocol):
    def resolve(self, company_id: int) -> CompanySeed:
        ...


class EnrichmentRepositoryPort(Protocol):
    def next_companies(self, limit: int = 3) -> list[int]:
        ...

    def next_enrichment_company_ids(self, limit: int = 40) -> list[int]:
        ...

    def persist_batch(
        self, batch: EnrichmentBatch, *, provider: str = "manual_ai_research"
    ) -> dict[str, Any]:
        ...


class TinyFishProviderPort(Protocol):
    def build_packet(
        self,
        *,
        company_id: int,
        domain: str,
        merchant_name: str | None = None,
        max_fetch_urls: int = 10,
    ) -> EnrichmentPacket:
        ...


class DatabaseCompanySeedResolver:
    """Resolve only canonical company identity fields needed by enrichment."""

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def resolve(self, company_id: int) -> CompanySeed:
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, domain, name FROM public.companies WHERE id = %s",
                (company_id,),
            )
            row = cur.fetchone()
        if row is None:
            raise ValueError(f"company {company_id} was not found")
        if not row[1]:
            raise ValueError(f"company {company_id} has no domain")
        return CompanySeed(company_id=row[0], domain=row[1], merchant_name=row[2])


class TinyFishBatchEnricher:
    """Run the bounded TinyFish research pipeline for the next 1-3 companies."""

    def __init__(
        self,
        repository: EnrichmentRepositoryPort,
        provider: TinyFishProviderPort,
        seed_resolver: CompanySeedResolver,
    ) -> None:
        self._repository = repository
        self._provider = provider
        self._seed_resolver = seed_resolver

    def build_next_batch(self, *, limit: int = 3) -> EnrichmentBatch:
        company_ids = self._repository.next_companies(limit=limit)
        packets: list[EnrichmentPacket] = []
        for company_id in company_ids:
            seed = self._seed_resolver.resolve(company_id)
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



@dataclass(frozen=True)
class TinyFishDailyRunResult:
    requested: int
    succeeded: int
    failed: int
    company_ids: list[int]
    failures: list[dict[str, object]]



class TinyFishDailyEnricher:
    """Continuously enrich a bounded daily slice, persisting each company independently."""

    def __init__(
        self,
        repository: EnrichmentRepositoryPort,
        provider: TinyFishProviderPort,
        seed_resolver: CompanySeedResolver,
    ) -> None:
        self._repository = repository
        self._provider = provider
        self._seed_resolver = seed_resolver

    def run_daily(self, *, limit: int = 40) -> TinyFishDailyRunResult:
        if not 1 <= limit <= 40:
            raise ValueError("daily enrichment limit must be between 1 and 40")
        company_ids = self._repository.next_enrichment_company_ids(limit=limit)
        succeeded = 0
        failures: list[dict[str, object]] = []
        for company_id in company_ids:
            try:
                seed = self._seed_resolver.resolve(company_id)
                packet = self._provider.build_packet(
                    company_id=seed.company_id,
                    domain=seed.domain,
                    merchant_name=seed.merchant_name,
                )
                self._repository.persist_batch(
                    EnrichmentBatch(packets=[packet]),
                    provider="tinyfish",
                )
                succeeded += 1
            except Exception as exc:
                failures.append(
                    {"company_id": company_id, "error": str(exc)}
                )
        return TinyFishDailyRunResult(
            requested=len(company_ids),
            succeeded=succeeded,
            failed=len(failures),
            company_ids=company_ids,
            failures=failures,
        )
