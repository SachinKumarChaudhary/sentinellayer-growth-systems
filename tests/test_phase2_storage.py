from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from sentinellayer_growth_engine.phase2.storage import (
    EvaluationResultRecord,
    Phase2RunRecord,
    ProviderAttemptRecord,
    ResearchObservationRecord,
)


NOW = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)


def test_run_record_defaults_and_non_negative_counters() -> None:
    record = Phase2RunRecord(
        run_id="00000000-0000-0000-0000-000000000001",
        request_key="lead:acme:phase2",
        contract_version="phase2.entity_resolution.v1",
        matching_version="phase2.deterministic_match.v1",
        started_at=NOW,
    )

    assert record.status == "RUNNING"
    assert record.input_count == 0
    assert record.metadata == {}


def test_run_record_rejects_negative_counters() -> None:
    with pytest.raises(ValidationError):
        Phase2RunRecord(
            run_id="00000000-0000-0000-0000-000000000001",
            request_key="lead:acme:phase2",
            contract_version="phase2.entity_resolution.v1",
            matching_version="phase2.deterministic_match.v1",
            started_at=NOW,
            candidate_count=-1,
        )


def test_provider_attempt_rejects_invalid_request_fingerprint() -> None:
    with pytest.raises(ValidationError):
        ProviderAttemptRecord(
            run_id="00000000-0000-0000-0000-000000000001",
            provider="tinyfish",
            operation="search",
            request_fingerprint="not-a-sha256",
            status="SUCCEEDED",
            started_at=NOW,
        )


def test_research_observation_preserves_search_provenance() -> None:
    record = ResearchObservationRecord(
        run_id="00000000-0000-0000-0000-000000000001",
        observation_id="obs-1",
        mission_id="mission-1",
        provider="tinyfish",
        observation_type="SEARCH_RESULT",
        result_position=0,
        url="https://example.com/about",
        source_domain="example.com",
        title="Example",
        snippet="Official company page.",
        observed_at=NOW,
        request_params={"purpose": "entity identity"},
        provenance={"provider_request_id": "req-1"},
        search_linked=True,
        observation_payload={"url": "https://example.com/about"},
    )

    assert record.search_linked is True
    assert record.provenance["provider_request_id"] == "req-1"


def test_evaluation_scores_are_bounded() -> None:
    with pytest.raises(ValidationError):
        EvaluationResultRecord(
            run_id="00000000-0000-0000-0000-000000000001",
            benchmark_version="phase2.gold.v1",
            case_id="case-1",
            entity_type_score=1.1,
            passed=False,
            expected_payload={},
            observed_payload={},
            evaluator_version="phase2.evaluator.v1",
        )
