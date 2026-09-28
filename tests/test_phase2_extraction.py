from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Self
from urllib.request import Request

import pytest

from sentinellayer_growth_engine.phase1.models import CanonicalLead, Phase1Handoff
from sentinellayer_growth_engine.phase2.extraction import (
    EvidenceInput,
    EntityEvidenceExtraction,
    GroqEntityEvidenceExtractor,
    GroqExtractionError,
    deterministic_extract_evidence,
    extract_with_fallback,
)


NOW = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)


def _lead() -> Phase1Handoff:
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
        platform=None,
        source_refs=["source-1"],
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
        lead_id="lead-1",
        canonical_lead=canonical,
        source_refs=["source-1"],
        field_observations=[],
        quality_status="ACCEPTED",
        quality_findings=[],
        normalization_version="phase1.v1",
        canonical_fingerprint=canonical.canonical_fingerprint,
        contract_version="phase1.handoff.v1",
        downstream_eligible=True,
        completed_at=NOW,
    )


def _evidence(text: str) -> list[EvidenceInput]:
    return [
        EvidenceInput(
            evidence_id="e1",
            url="https://brand.example/about",
            title="About BrandCo",
            text=text,
        )
    ]


def test_extraction_schema_rejects_final_decision_fields() -> None:
    with pytest.raises(ValueError):
        EntityEvidenceExtraction.model_validate(
            {
                "candidate_entities": [],
                "relationship_claims": [],
                "currentness_claims": [],
                "conflicts": [],
                "evidence_spans": [],
                "canonical_entity_id": "forbidden",
            }
        )


def test_deterministic_fallback_extracts_relationship_evidence() -> None:
    result = deterministic_extract_evidence(
        lead=_lead(),
        evidence=_evidence("BrandCo is operated by Example Holdings."),
    )

    assert len(result.candidate_entities) == 1
    candidate = result.candidate_entities[0]
    assert candidate.name == "Example Holdings"
    assert candidate.relationship_to_target == "OPERATED_BY"
    assert candidate.evidence_ids == ["e1"]

    assert len(result.relationship_claims) == 1
    relationship = result.relationship_claims[0]
    assert relationship.subject_name == "BrandCo"
    assert relationship.object_name == "Example Holdings"
    assert relationship.evidence_ids == ["e1"]

    assert result.evidence_spans[0].evidence_id == "e1"
    assert "operated by Example Holdings" in result.evidence_spans[0].quote


def test_evidence_reference_validation_rejects_unknown_ids() -> None:
    result = EntityEvidenceExtraction.model_validate(
        {
            "candidate_entities": [
                {
                    "name": "Example Holdings",
                    "entity_type": "OPERATING_ENTITY",
                    "domain": None,
                    "relationship_to_target": "OPERATED_BY",
                    "evidence_ids": ["missing"],
                }
            ]
        }
    )

    with pytest.raises(GroqExtractionError, match="unknown evidence ids"):
        GroqEntityEvidenceExtractor._validate_evidence_refs(result, _evidence("Known evidence"))


def test_groq_payload_is_strict_and_contains_no_final_decision_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[dict[str, object]] = []

    class FakeResponse:
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *args: object) -> bool:
            return False

        def read(self) -> bytes:
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "candidate_entities": [],
                                        "relationship_claims": [],
                                        "currentness_claims": [],
                                        "conflicts": [],
                                        "evidence_spans": [],
                                    }
                                )
                            }
                        }
                    ]
                }
            ).encode("utf-8")

    def fake_urlopen(request: Request, timeout: float) -> FakeResponse:
        assert request.data is not None
        requests.append(json.loads(request.data.decode("utf-8")))
        return FakeResponse()

    monkeypatch.setattr(
        "sentinellayer_growth_engine.phase2.extraction.urlopen",
        fake_urlopen,
    )

    extractor = GroqEntityEvidenceExtractor(api_key="test-key")
    result = extractor.extract(
        lead=_lead(),
        evidence=_evidence("BrandCo is operated by Example Holdings."),
    )

    assert result.candidate_entities == []
    payload = requests[0]
    response_format = payload["response_format"]
    assert isinstance(response_format, dict)
    json_schema = response_format["json_schema"]
    assert isinstance(json_schema, dict)
    assert json_schema["strict"] is True
    schema_text = json.dumps(json_schema["schema"])
    for forbidden in (
        "canonical_entity_id",
        "MATCHED",
        "AMBIGUOUS",
        "CONFLICT",
        "UNRESOLVED",
        "NO_MATCH",
        "buyer_role",
        "buying_intent",
    ):
        assert forbidden not in schema_text


def test_malformed_groq_response_uses_deterministic_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        def __enter__(self) -> "FakeResponse":
            return self

        def __exit__(self, *args: object) -> bool:
            return False

        def read(self) -> bytes:
            return b"{not-json"

    def fake_urlopen(request: Request, timeout: float) -> FakeResponse:
        return FakeResponse()

    monkeypatch.setattr(
        "sentinellayer_growth_engine.phase2.extraction.urlopen",
        fake_urlopen,
    )

    extractor = GroqEntityEvidenceExtractor(api_key="test-key", max_attempts=1)

    result, mode = extract_with_fallback(
        extractor=extractor,
        lead=_lead(),
        evidence=_evidence("BrandCo is operated by Example Holdings."),
    )

    assert mode == "deterministic"
    assert result.candidate_entities[0].name == "Example Holdings"
