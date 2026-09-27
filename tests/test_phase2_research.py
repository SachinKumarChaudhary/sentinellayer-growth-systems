from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from sentinellayer_growth_engine.phase2.research import (
    ResearchMission,
    TinyFishResearchAdapter,
    TinyFishSearchRequest,
)
from sentinellayer_growth_engine.tinyfish_client import (
    TinyFishFetchResult,
    TinyFishSearchResult,
)


class FakeTinyFishClient:
    def __init__(self) -> None:
        self.search_calls: list[dict[str, object]] = []
        self.fetch_calls: list[dict[str, object]] = []

    def search(self, query: str, **kwargs: object) -> list[TinyFishSearchResult]:
        self.search_calls.append({"query": query, **kwargs})
        return [
            TinyFishSearchResult(
                title="Official company page",
                url="https://brand.example/about",
                snippet="BrandCo is operated by Example Holdings.",
            )
        ]

    def fetch(self, urls: list[str], **kwargs: object) -> list[TinyFishFetchResult]:
        self.fetch_calls.append({"urls": urls, **kwargs})
        return [
            TinyFishFetchResult(
                url=urls[0],
                final_url=urls[0],
                title="About",
                text="BrandCo is operated by Example Holdings.",
                published_date="2026-09-01",
            )
        ]


MISSION = ResearchMission(
    mission_id="mission-1",
    lead_id="lead-1",
    mission_type="entity_identity",
    objective="Determine whether the supplied domain is operated by the candidate organization.",
    required_evidence=("official_identity", "operating_entity"),
)


def test_search_request_rejects_mixed_temporal_modes() -> None:
    with pytest.raises(ValueError, match="cannot be combined"):
        TinyFishSearchRequest(
            query="BrandCo operating entity",
            recency_minutes=60,
            after_date=date(2026, 9, 1),
        )


def test_search_request_rejects_reversed_date_range() -> None:
    with pytest.raises(ValueError, match="on or before"):
        TinyFishSearchRequest(
            query="BrandCo acquired",
            after_date=date(2026, 9, 20),
            before_date=date(2026, 9, 1),
        )


def test_search_request_rejects_research_paper_for_phase2() -> None:
    with pytest.raises(ValueError, match="outside normal Phase 2"):
        TinyFishSearchRequest(
            query="BrandCo",
            domain_type="research_paper",
        )


def test_search_request_preserves_canonical_provider_parameters() -> None:
    request = TinyFishSearchRequest(
        query='"BrandCo" parent company ownership',
        purpose="Determine the current parent relationship.",
        location="US",
        language="en",
        include_domains=("brand.example", "parent.example"),
        exclude_domains=("reddit.com",),
        after_date=date(2026, 8, 1),
        before_date=date(2026, 9, 27),
        domain_type="web",
        page=1,
    )

    params = request.params()

    assert params["query"] == '"BrandCo" parent company ownership'
    assert params["include_domains"] == "brand.example,parent.example"
    assert params["exclude_domains"] == "reddit.com"
    assert params["after_date"] == "2026-08-01"
    assert params["before_date"] == "2026-09-27"
    assert params["page"] == "1"


def test_search_observations_preserve_request_and_source_provenance() -> None:
    client = FakeTinyFishClient()
    adapter = TinyFishResearchAdapter(client)  # type: ignore[arg-type]
    request = TinyFishSearchRequest(
        query='"BrandCo" operating entity',
        purpose="Resolve operating entity.",
        include_domains=("brand.example",),
    )

    observations = adapter.search(
        MISSION,
        request,
        provider_request_id="req-123",
        observed_at=datetime(2026, 9, 27, 12, 0, tzinfo=UTC),
    )

    assert len(observations) == 1
    observation = observations[0]
    assert observation.provider == "tinyfish_search"
    assert observation.provider_request_id == "req-123"
    assert observation.mission_id == "mission-1"
    assert observation.result_position == 0
    assert observation.source_domain == "brand.example"
    assert observation.request_parameters["include_domains"] == "brand.example"


def test_fetch_observations_link_back_to_search_urls() -> None:
    client = FakeTinyFishClient()
    adapter = TinyFishResearchAdapter(client)  # type: ignore[arg-type]

    observations = adapter.fetch(
        MISSION,
        ["https://brand.example/about"],
        provider_request_id="fetch-123",
        purpose="Inspect official identity evidence.",
        fetched_at=datetime(2026, 9, 27, 12, 1, tzinfo=UTC),
    )

    assert len(observations) == 1
    observation = observations[0]
    assert observation.provider == "tinyfish_fetch"
    assert observation.search_linked is True
    assert observation.published_at == "2026-09-01"
