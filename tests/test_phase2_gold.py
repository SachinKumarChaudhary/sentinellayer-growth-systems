from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from sentinellayer_growth_engine.phase1.models import CanonicalLead, Phase1Handoff
from sentinellayer_growth_engine.phase2.models import EntityCandidate, EntityRelationship
from sentinellayer_growth_engine.phase2.resolver import resolve_entity


NOW = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)
FIXTURE = Path(__file__).parent / "fixtures" / "phase2_gold.json"


def _handoff(case_id: str, lead: dict[str, Any]) -> Phase1Handoff:
    domain = cast(str | None, lead.get("domain"))
    country_code = cast(str | None, lead.get("country_code"))
    name = cast(str, lead["name"])

    canonical = CanonicalLead(
        schema_version="v1",
        lead_id=f"gold-{case_id}",
        display_name=name,
        legal_name=None,
        domain=domain,
        canonical_url=f"https://{domain}" if domain else None,
        country_code=country_code,
        region=None,
        city=None,
        postal_code=None,
        platform=None,
        source_refs=[f"gold-source-{case_id}"],
        field_observations=[],
        normalization_version="phase1.v1",
        raw_fingerprint=("a" * 63) + "1",
        source_fingerprint=("b" * 63) + "2",
        canonical_fingerprint=("c" * 63) + "3",
        quality_status="ACCEPTED",
        quality_finding_ids=[],
        created_at=NOW,
        updated_at=NOW,
    )
    return Phase1Handoff(
        schema_version="v1",
        lead_id=canonical.lead_id,
        canonical_lead=canonical,
        source_refs=canonical.source_refs,
        field_observations=[],
        quality_status="ACCEPTED",
        quality_findings=[],
        normalization_version="phase1.v1",
        canonical_fingerprint=canonical.canonical_fingerprint,
        contract_version="phase1.handoff.v1",
        downstream_eligible=True,
        completed_at=NOW,
    )


def _candidate(raw: dict[str, Any]) -> EntityCandidate:
    return EntityCandidate.model_validate(raw)


def _relationship(raw: dict[str, Any]) -> EntityRelationship:
    return EntityRelationship.model_validate(raw)


def test_phase2_gold_cases_match_expected_deterministic_outcomes() -> None:
    dataset = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert dataset["schema_version"] == "phase2.gold.v1"

    for case in dataset["cases"]:
        lead = _handoff(case["id"], case["lead"])
        candidates = [_candidate(item) for item in case["candidates"]]
        relationships = [
            _relationship(item) for item in case.get("relationships", [])
        ]
        decision = resolve_entity(
            lead,
            candidates,
            relationships=relationships or None,
            now=NOW,
        )

        expected = case["expected"]
        assert decision.status == expected["status"], case["id"]
        assert decision.canonical_entity_id == expected["canonical_entity_id"], case["id"]
        assert decision.confidence == expected["confidence"], case["id"]
        assert decision.decision_trace, case["id"]
