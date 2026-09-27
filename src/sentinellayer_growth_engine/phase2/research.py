from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Literal
from urllib.parse import urlencode

from ..tinyfish_client import TinyFishClient, TinyFishFetchResult, TinyFishSearchResult
from .models import EntityCandidate


DomainType = Literal["web", "news", "research_paper"]


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC)


class TinyFishSearchRequest:
    def __init__(
        self,
        *,
        query: str,
        purpose: str | None = None,
        location: str | None = None,
        language: str | None = None,
        include_domains: tuple[str, ...] = (),
        exclude_domains: tuple[str, ...] = (),
        recency_minutes: int | None = None,
        after_date: date | None = None,
        before_date: date | None = None,
        domain_type: DomainType = "web",
        page: int = 0,
    ) -> None:
        if not query.strip():
            raise ValueError("query must not be empty")
        if purpose is not None and len(purpose) > 2000:
            raise ValueError("purpose must be at most 2000 characters")
        if recency_minutes is not None and not 1 <= recency_minutes <= 5_256_000:
            raise ValueError("recency_minutes must be between 1 and 5,256,000")
        if recency_minutes is not None and (after_date is not None or before_date is not None):
            raise ValueError("recency_minutes cannot be combined with absolute date bounds")
        if after_date is not None and before_date is not None and after_date > before_date:
            raise ValueError("after_date must be on or before before_date")
        if domain_type != "research_paper" and (False):
            raise AssertionError("unreachable")
        if domain_type != "research_paper" and False:
            raise AssertionError("unreachable")
        if page < 0 or page > 10:
            raise ValueError("page must be between 0 and 10")
        if domain_type == "research_paper":
            raise ValueError("research_paper is outside normal Phase 2 entity research")

        self.query = query
        self.purpose = purpose
        self.location = location
        self.language = language
        self.include_domains = include_domains
        self.exclude_domains = exclude_domains
        self.recency_minutes = recency_minutes
        self.after_date = after_date
        self.before_date = before_date
        self.domain_type = domain_type
        self.page = page

    def params(self) -> dict[str, str]:
        result: dict[str, str] = {"query": self.query, "page": str(self.page)}
        optional = {
            "purpose": self.purpose,
            "location": self.location,
            "language": self.language,
            "include_domains": ",".join(self.include_domains) if self.include_domains else None,
            "exclude_domains": ",".join(self.exclude_domains) if self.exclude_domains else None,
            "recency_minutes": str(self.recency_minutes) if self.recency_minutes is not None else None,
            "after_date": self.after_date.isoformat() if self.after_date else None,
            "before_date": self.before_date.isoformat() if self.before_date else None,
            "domain_type": self.domain_type,
        }
        result.update({key: value for key, value in optional.items() if value is not None})
        return result

    def query_string(self) -> str:
        return urlencode(self.params())


class ResearchMission:
    def __init__(
        self,
        *,
        mission_id: str,
        lead_id: str,
        mission_type: str,
        objective: str,
        required_evidence: tuple[str, ...],
        stopping_threshold: str = "sufficient_material_evidence",
    ) -> None:
        for value, name in (
            (mission_id, "mission_id"),
            (lead_id, "lead_id"),
            (mission_type, "mission_type"),
            (objective, "objective"),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be empty")
        self.mission_id = mission_id
        self.lead_id = lead_id
        self.mission_type = mission_type
        self.objective = objective
        self.required_evidence = required_evidence
        self.stopping_threshold = stopping_threshold


class TinyFishSearchObservation:
    def __init__(
        self,
        *,
        provider_request_id: str,
        mission_id: str,
        result_position: int,
        result: TinyFishSearchResult,
        request: TinyFishSearchRequest,
        observed_at: datetime,
    ) -> None:
        self.provider = "tinyfish_search"
        self.provider_request_id = provider_request_id
        self.mission_id = mission_id
        self.result_position = result_position
        self.title = result.title
        self.url = result.url
        self.snippet = result.snippet
        self.query = request.query
        self.request_parameters = request.params()
        self.observed_at = _utc(observed_at)
        self.source_domain = result.url.split("/", 3)[2].lower() if "://" in result.url else ""


class TinyFishFetchObservation:
    def __init__(
        self,
        *,
        provider_request_id: str,
        mission_id: str,
        result: TinyFishFetchResult,
        search_urls: tuple[str, ...],
        fetched_at: datetime,
    ) -> None:
        self.provider = "tinyfish_fetch"
        self.provider_request_id = provider_request_id
        self.mission_id = mission_id
        self.url = result.url
        self.final_url = result.final_url
        self.title = result.title
        self.text = result.text
        self.published_at = result.published_date
        self.fetched_at = _utc(fetched_at)
        self.search_linked = result.url in search_urls or bool(
            result.final_url and result.final_url in search_urls
        )


class TinyFishResearchAdapter:
    """Provider boundary for Phase 2 research.

    TinyFish outputs observations only. No EntityResolutionDecision is produced
    or mutated by this adapter.
    """

    def __init__(self, client: TinyFishClient) -> None:
        self.client = client

    def search(
        self,
        mission: ResearchMission,
        request: TinyFishSearchRequest,
        *,
        provider_request_id: str,
        observed_at: datetime | None = None,
    ) -> list[TinyFishSearchObservation]:
        stamp = observed_at or datetime.now(UTC)
        results = self.client.search(
            request.query,
            purpose=request.purpose,
            location=request.location,
            language=request.language,
            include_domains=request.include_domains,
            exclude_domains=request.exclude_domains,
            recency_minutes=request.recency_minutes,
            after_date=request.after_date.isoformat() if request.after_date else None,
            before_date=request.before_date.isoformat() if request.before_date else None,
            domain_type=request.domain_type,
            page=request.page,
        )
        return [
            TinyFishSearchObservation(
                provider_request_id=provider_request_id,
                mission_id=mission.mission_id,
                result_position=index,
                result=result,
                request=request,
                observed_at=stamp,
            )
            for index, result in enumerate(results)
        ]

    def fetch(
        self,
        mission: ResearchMission,
        urls: list[str],
        *,
        provider_request_id: str,
        purpose: str | None = None,
        fetched_at: datetime | None = None,
    ) -> list[TinyFishFetchObservation]:
        stamp = fetched_at or datetime.now(UTC)
        results = self.client.fetch(
            urls,
            purpose=purpose,
            format="markdown",
            include_links=False,
            include_image_links=False,
            include_page_metadata=True,
        )
        search_urls = tuple(urls)
        return [
            TinyFishFetchObservation(
                provider_request_id=provider_request_id,
                mission_id=mission.mission_id,
                result=result,
                search_urls=search_urls,
                fetched_at=stamp,
            )
            for result in results
        ]


def candidate_from_research(
    *,
    candidate_id: str,
    canonical_name: str,
    canonical_domain: str | None,
    entity_type: str = "UNKNOWN",
    evidence_refs: list[str] | None = None,
) -> EntityCandidate:
    """Create a bounded candidate from research evidence.

    This helper creates a candidate only; it cannot create or mutate a final
    resolution decision.
    """

    return EntityCandidate(
        candidate_id=candidate_id,
        entity_type=entity_type,  # type: ignore[arg-type]
        canonical_name=canonical_name,
        canonical_domain=canonical_domain,
        evidence_refs=evidence_refs or [],
        origin="research",
    )
