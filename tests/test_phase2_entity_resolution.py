from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sentinellayer_growth_engine.phase1.models import (
    CanonicalLead,
    Phase1Handoff,
)
from sentinellayer_growth_engine.phase2.blocking import generate_candidates
from sentinellayer_growth_engine.phase2.models import EntityCandidate, EntityRelationship
from sentinellayer_growth_engine.phase2.resolver import resolve_entity


NOW = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)


def make_lead(
    *,
    name: str = "Acme",
    domain: str | None = "acme.example",
    country: str | None = "US",
    lead_id: str = "lead-1",
) -> Phase1Handoff:
    canonical = CanonicalLead(
        schema_version="v1",
        lead_id=lead_id,
        display_name=name,
        legal_name=None,
        domain=domain,
        canonical_url=f"https://{domain}" if domain else None,
        country_code=country,
        region=None,
        city=None,
        postal_code=None,
        platform=None,
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
        lead_id=lead_id,
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


def candidate(
    *,
    candidate_id: str,
    entity_id: str | None = None,
    name: str = "Acme",
    domain: str | None = "acme.example",
    verified: bool = False,
    official_tie: bool = False,
    geography: list[str] | None = None,
    **kwargs: object,
) -> EntityCandidate:
    return EntityCandidate(
        candidate_id=candidate_id,
        entity_id=entity_id,
        entity_type="LEGAL_ENTITY",
        canonical_name=name,
        canonical_domain=domain,
        domain_verified=verified,
        explicit_official_identity_tie=official_tie,
        geography=geography or ["US"],
        currentness="CURRENT",
        evidence_refs=[f"https://evidence.example/{candidate_id}"],
        **kwargs,
    )


def test_exact_verified_domain_matches_with_high_confidence() -> None:
    decision = resolve_entity(
        make_lead(),
        [candidate(candidate_id="acme-inc", entity_id="entity-acme", verified=True)],
        now=NOW,
    )

    assert decision.status == "MATCHED"
    assert decision.confidence == "high"
    assert decision.canonical_entity_id == "entity-acme"
    assert "exact_verified_canonical_domain" in decision.decisive_signals
    assert decision.research_required is False


def test_same_name_without_strong_identity_stays_ambiguous() -> None:
    decision = resolve_entity(
        make_lead(domain=None),
        [
            candidate(candidate_id="acme-east", domain="acme-east.example"),
            candidate(candidate_id="acme-west", domain="acme-west.example"),
        ],
        now=NOW,
    )

    assert decision.status == "AMBIGUOUS"
    assert decision.research_required is True
    assert decision.canonical_entity_id is None


def test_multiple_strong_candidates_return_conflict() -> None:
    decision = resolve_entity(
        make_lead(),
        [
            candidate(candidate_id="entity-a", entity_id="a", verified=True),
            candidate(candidate_id="entity-b", entity_id="b", verified=True),
        ],
        now=NOW,
    )

    assert decision.status == "CONFLICT"
    assert decision.research_required is True
    assert "currentness" in decision.research_missions


def test_external_provider_is_not_accepted_as_target_entity() -> None:
    decision = resolve_entity(
        make_lead(),
        [
            candidate(
                candidate_id="provider",
                domain="provider.example",
                external_provider_relationship=True,
                official_tie=True,
            )
        ],
        now=NOW,
    )

    assert decision.status == "NO_MATCH"
    assert "provider" in decision.rejected_candidates


def test_relationship_is_separate_and_visible() -> None:
    relationship = EntityRelationship(
        relationship_id="rel-1",
        subject_entity_id="brand-1",
        predicate="OWNED_BY",
        object_entity_id="parent-1",
        currentness="CURRENT",
        evidence_refs=["https://evidence.example/ownership"],
        status="ESTABLISHED",
        adjudication_reason="Official parent-company page identifies current ownership.",
    )
    decision = resolve_entity(
        make_lead(name="BrandCo", domain="brand.example"),
        [
            candidate(
                candidate_id="brand-1",
                entity_id="brand-1",
                name="BrandCo",
                domain="brand.example",
                verified=True,
            )
        ],
        relationships=[relationship],
        now=NOW,
    )

    assert decision.status == "MATCHED_WITH_RELATIONSHIP"
    assert decision.relationships[0].predicate == "OWNED_BY"
    assert decision.relationships[0].object_entity_id == "parent-1"


def test_candidate_generation_is_bounded() -> None:
    lead = make_lead()
    candidates = [
        candidate(candidate_id=f"c-{index}", name="Acme", domain=f"acme-{index}.example")
        for index in range(30)
    ]

    selected = generate_candidates(lead, candidates, budget=7)

    assert len(selected) == 7
    assert [item.candidate_id for item in selected] == [f"c-{i}" for i in range(7)]


def test_candidate_budget_must_be_positive() -> None:
    with pytest.raises(ValueError):
        generate_candidates(make_lead(), [], budget=0)
