from __future__ import annotations

from sentinellayer_growth_engine.contracts import validate_contract
from sentinellayer_growth_engine.phase1.models import CanonicalLead, Phase1Handoff
from sentinellayer_growth_engine.phase2.models import EntityCandidate
from sentinellayer_growth_engine.phase2.resolver import resolve_entity

from datetime import UTC, datetime


def _lead() -> Phase1Handoff:
    now = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)
    canonical = CanonicalLead(
        schema_version="v1",
        lead_id="lead-1",
        display_name="Acme",
        legal_name=None,
        domain="acme.example",
        canonical_url="https://acme.example",
        country_code="US",
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
        created_at=now,
        updated_at=now,
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
        completed_at=now,
    )


def test_phase2_decision_matches_json_schema() -> None:
    lead = _lead()
    candidate = EntityCandidate(
        candidate_id="candidate-1",
        entity_id="entity-1",
        entity_type="LEGAL_ENTITY",
        canonical_name="Acme",
        canonical_domain="acme.example",
        domain_verified=True,
        currentness="CURRENT",
        evidence_refs=["https://evidence.example/acme"],
    )

    decision = resolve_entity(lead, [candidate], now=lead.completed_at)
    payload = decision.model_dump(mode="json")

    validate_contract("entity_resolution_decision", payload)


def test_phase2_schema_rejects_missing_decision_id() -> None:
    bad_payload = {
        "contract_version": "phase2.entity_resolution.v1",
        "lead_id": "lead-1",
        "status": "MATCHED",
        "entity_type": "LEGAL_ENTITY",
        "confidence": "high",
        "decisive_signals": [],
        "rejected_candidates": [],
        "comparisons": [],
        "decision_trace": [],
        "evidence_refs": [],
        "currentness": "CURRENT",
        "relationships": [],
        "research_required": False,
        "research_missions": [],
        "unresolved_questions": [],
        "matching_version": "phase2.deterministic_match.v1",
        "decided_at": "2026-09-25T12:00:00Z",
    }

    try:
        validate_contract("entity_resolution_decision", bad_payload)
    except ValueError as exc:
        assert "decision_id" in str(exc)
    else:
        raise AssertionError("schema unexpectedly accepted payload without decision_id")
