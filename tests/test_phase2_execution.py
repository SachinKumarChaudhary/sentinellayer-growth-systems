from __future__ import annotations

from datetime import UTC, datetime

from sentinellayer_growth_engine.phase1.models import CanonicalLead, Phase1Handoff
from sentinellayer_growth_engine.phase2.execution import (
    Phase2BatchExecutor,
    Phase2CandidateSet,
    Phase2ProviderUnavailable,
)
from sentinellayer_growth_engine.phase2.models import EntityCandidate
from sentinellayer_growth_engine.phase2.storage import Phase2RunRecord


NOW = datetime(2026, 9, 28, 6, 0, tzinfo=UTC)


def _handoff(lead_id: str = "lead-1") -> Phase1Handoff:
    canonical = CanonicalLead(
        schema_version="v1",
        lead_id=lead_id,
        display_name="BrandCo",
        legal_name="BrandCo LLC",
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


class FakePhase1Source:
    def __init__(self, handoffs: list[Phase1Handoff]) -> None:
        self.handoffs = handoffs

    def list_handoffs(
        self,
        *,
        downstream_eligible: bool = True,
        limit: int | None = None,
    ) -> list[Phase1Handoff]:
        assert downstream_eligible is True
        return self.handoffs[:limit] if limit is not None else self.handoffs


class FakePhase2Persistence:
    def __init__(self) -> None:
        self.runs: dict[str, Phase2RunRecord] = {}
        self.decisions = []

    def create_run(self, run: Phase2RunRecord) -> Phase2RunRecord:
        existing = self.runs.get(run.request_key)
        if existing is not None:
            return existing
        self.runs[run.request_key] = run
        return run

    def persist_resolution(self, **kwargs: object) -> bool:
        self.decisions.append(kwargs)
        return True

    def complete_run(
        self,
        *,
        run_id: str,
        status: str,
        completed_at: datetime,
        metadata: dict[str, object] | None = None,
    ) -> None:
        current = next(item for item in self.runs.values() if item.run_id == run_id)
        current.status = status  # type: ignore[assignment]
        current.completed_at = completed_at
        if metadata:
            current.metadata.update(metadata)
        current.input_count = len(self.decisions)
        current.decision_count = len(self.decisions)


def _candidate() -> EntityCandidate:
    return EntityCandidate(
        candidate_id="candidate-1",
        entity_id="entity-1",
        entity_type="LEGAL_ENTITY",
        canonical_name="BrandCo LLC",
        canonical_domain="brand.example",
        official_url="https://brand.example",
        domain_verified=True,
        currentness="CURRENT",
        evidence_refs=["https://brand.example/about"],
        origin="provider",
    )


def test_batch_executor_persists_deterministic_resolution() -> None:
    source = FakePhase1Source([_handoff()])
    persistence = FakePhase2Persistence()
    executor = Phase2BatchExecutor(source, persistence)

    result = executor.run(
        request_key="phase2-test-1",
        candidate_provider=lambda _handoff: Phase2CandidateSet(candidates=[_candidate()]),
        now=NOW,
    )

    assert result.input_count == 1
    assert result.decision_count == 1
    assert result.matched_count == 1
    assert result.research_required_count == 0
    assert result.provider_error_count == 0
    assert len(persistence.decisions) == 1


def test_batch_executor_treats_provider_failure_as_unresolved_not_no_match() -> None:
    source = FakePhase1Source([_handoff()])
    persistence = FakePhase2Persistence()
    executor = Phase2BatchExecutor(source, persistence)

    def failing_provider(_handoff: Phase1Handoff) -> Phase2CandidateSet:
        raise Phase2ProviderUnavailable("provider unavailable")

    result = executor.run(
        request_key="phase2-test-2",
        candidate_provider=failing_provider,
        now=NOW,
    )

    assert result.provider_error_count == 1
    stored = persistence.decisions[0]["decision"]
    assert stored.status == "UNRESOLVED"
    assert stored.canonical_entity_id is None


def test_completed_request_key_is_a_noop() -> None:
    source = FakePhase1Source([_handoff()])
    persistence = FakePhase2Persistence()
    executor = Phase2BatchExecutor(source, persistence)

    first = executor.run(
        request_key="phase2-test-3",
        candidate_provider=lambda _handoff: Phase2CandidateSet(candidates=[_candidate()]),
        now=NOW,
    )
    calls = len(persistence.decisions)

    second = executor.run(
        request_key="phase2-test-3",
        candidate_provider=lambda _handoff: (_ for _ in ()).throw(
            AssertionError("provider must not run on a completed replay")
        ),
        now=NOW,
    )

    assert second.run_id == first.run_id
    assert second.decision_count == first.decision_count
    assert len(persistence.decisions) == calls
