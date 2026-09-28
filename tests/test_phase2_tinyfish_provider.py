from __future__ import annotations

from datetime import UTC, datetime

from sentinellayer_growth_engine.phase1.models import CanonicalLead, Phase1Handoff
from sentinellayer_growth_engine.phase2.extraction import (
    CandidateEntityExtraction,
    EntityEvidenceExtraction,
)
from sentinellayer_growth_engine.phase2.research import TinyFishResearchAdapter
from sentinellayer_growth_engine.phase2.tinyfish_provider import (
    TinyFishEntityCandidateProvider,
    TinyFishTelemetryBuffer,
)
from sentinellayer_growth_engine.tinyfish_client import (
    TinyFishFetchResult,
    TinyFishSearchResult,
)


NOW = datetime(2026, 9, 28, 6, 0, tzinfo=UTC)


def _handoff() -> Phase1Handoff:
    canonical = CanonicalLead(
        schema_version="v1",
        lead_id="lead-1",
        display_name="BrandCo",
        legal_name=None,
        domain="brand.example",
        canonical_url="https://brand.example",
        country_code="US",
        region=None,
        city=None,
        postal_code=None,
        platform="shopify",
        source_refs=["source-1"],
        field_observations=[],
        normalization_version="phase1.v1",
        raw_fingerprint="a" * 64,
        source_fingerprint="b" * 64,
        canonical_fingerprint="c" * 64,
        quality_status="ACCEPTED",
        quality_finding_ids=[],
        created_at=NOW,
        updated_at=NOW,
    )
    return Phase1Handoff(
        schema_version="v1",
        lead_id="lead-1",
        canonical_lead=canonical,
        source_refs=["source-1"],
        field_observations=[],
        quality_status="ACCEPTED",
        quality_findings=[],
        normalization_version="phase1.v1",
        canonical_fingerprint="c" * 64,
        contract_version="phase1.handoff.v1",
        downstream_eligible=True,
        completed_at=NOW,
    )


class FakeClient:
    def __init__(self) -> None:
        self.search_calls: list[dict[str, object]] = []
        self.fetch_calls: list[dict[str, object]] = []

    def search(self, query: str, **kwargs: object) -> list[TinyFishSearchResult]:
        self.search_calls.append({"query": query, **kwargs})
        return [
            TinyFishSearchResult(
                title=f"BrandCo page {index}",
                url=f"https://brand.example/page-{index}",
                snippet="BrandCo is operated by BrandCo LLC.",
            )
            for index in range(10)
        ]

    def fetch(self, urls: list[str], **kwargs: object) -> list[TinyFishFetchResult]:
        self.fetch_calls.append({"urls": urls, **kwargs})
        return [
            TinyFishFetchResult(
                url=url,
                final_url=url,
                title="About BrandCo",
                text="BrandCo is operated by BrandCo LLC.",
                published_date="2026-09-01",
            )
            for url in urls
        ]


class FakeRepository:
    def __init__(self) -> None:
        self.observations = []
        self.attempts = []

    def persist_research_observation(self, observation: object) -> None:
        self.observations.append(observation)

    def persist_provider_attempt(self, attempt: object) -> None:
        self.attempts.append(attempt)


def test_tinyfish_provider_respects_search_and_fetch_budgets() -> None:
    client = FakeClient()
    repository = FakeRepository()
    provider = TinyFishEntityCandidateProvider(
        TinyFishResearchAdapter(client),  # type: ignore[arg-type]
        repository,  # type: ignore[arg-type]
        TinyFishTelemetryBuffer(),
        max_search_results=3,
        max_fetch_urls=2,
    )
    provider.bind_run("run-1")

    candidate_set = provider.discover(_handoff())

    assert len(client.search_calls) == 1
    assert len(client.fetch_calls) == 1
    assert len(client.fetch_calls[0]["urls"]) == 2
    assert len(repository.observations) == 5
    assert len(candidate_set.candidates) == 2

    relationship_candidate = next(
        candidate
        for candidate in candidate_set.candidates
        if candidate.canonical_name == "BrandCo LLC"
    )
    assert relationship_candidate.canonical_domain is None
    assert relationship_candidate.entity_id is None
    assert relationship_candidate.domain_verified is False
    assert relationship_candidate.official_corporate_url_match is False
    assert relationship_candidate.explicit_official_identity_tie is False

    fallback_candidate = next(
        candidate
        for candidate in candidate_set.candidates
        if candidate.entity_type == "BRAND"
    )
    assert fallback_candidate.canonical_name == "BrandCo"
    assert fallback_candidate.canonical_domain == "brand.example"
    assert fallback_candidate.entity_id is None
    assert fallback_candidate.domain_verified is True
    assert fallback_candidate.official_corporate_url_match is True
    assert fallback_candidate.explicit_official_identity_tie is True
    assert fallback_candidate.origin == "research"


def test_tinyfish_provider_requires_run_binding() -> None:
    client = FakeClient()
    provider = TinyFishEntityCandidateProvider(
        TinyFishResearchAdapter(client),  # type: ignore[arg-type]
        FakeRepository(),  # type: ignore[arg-type]
        TinyFishTelemetryBuffer(),
    )

    try:
        provider.discover(_handoff())
    except RuntimeError as exc:
        assert "bound to a Phase 2 run" in str(exc)
    else:
        raise AssertionError("provider must reject unbound execution")


def test_first_party_subdomain_supports_identity_candidate() -> None:
    evidence = [
        # The IR subdomain is first-party evidence for the canonical domain.
        {
            "evidence_id": "ir-1",
            "url": "https://ir.brand.example/company-information",
            "title": "Company Information",
            "text": "BrandCo Technologies Inc.",
        }
    ]
    extracted = EntityEvidenceExtraction.model_validate(
        {
            "candidate_entities": [
                {
                    "name": "BrandCo Technologies Inc.",
                    "entity_type": "LEGAL_ENTITY",
                    "domain": None,
                    "relationship_to_target": None,
                    "evidence_ids": ["ir-1"],
                }
            ],
            "relationship_claims": [],
            "currentness_claims": [],
            "conflicts": [],
            "evidence_spans": [],
        }
    )

    candidates = TinyFishEntityCandidateProvider._candidate_objects(
        _handoff(),
        extracted,
        [
            type("Evidence", (), {
                "evidence_id": "ir-1",
                "url": "https://ir.brand.example/company-information",
                "title": "Company Information",
                "text": "BrandCo Technologies Inc.",
            })()
        ],
    )

    candidate = next(item for item in candidates if item.canonical_name == "BrandCo Technologies Inc.")
    assert candidate.canonical_domain == "brand.example"
    assert candidate.domain_verified is True
    assert candidate.official_corporate_url_match is True
    assert candidate.explicit_official_identity_tie is False
