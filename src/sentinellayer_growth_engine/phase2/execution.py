from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, cast
from uuid import uuid4

from ..phase1.models import Phase1Handoff
from .models import (
    EntityCandidate,
    EntityRelationship,
    EntityResolutionDecision,
    MATCHING_VERSION,
    PHASE2_CONTRACT_VERSION,
)
from .resolver import resolve_entity
from .storage import Phase2RunRecord


@dataclass(frozen=True)
class Phase2CandidateSet:
    candidates: Sequence[EntityCandidate] = ()
    relationships: Sequence[EntityRelationship] = ()


class Phase2CandidateProvider(Protocol):
    def discover(self, handoff: Phase1Handoff) -> Phase2CandidateSet:
        """Return bounded candidate/evidence-derived inputs; never a final decision."""


class Phase1HandoffSource(Protocol):
    def list_handoffs(
        self,
        *,
        downstream_eligible: bool = True,
        limit: int | None = None,
    ) -> list[Phase1Handoff]:
        ...


class Phase2Persistence(Protocol):
    def create_run(self, run: Phase2RunRecord) -> Phase2RunRecord:
        ...

    def persist_resolution(
        self,
        *,
        run_id: str,
        lead_id: str,
        candidates: Sequence[EntityCandidate],
        comparisons: Sequence[Any],
        relationships: Sequence[EntityRelationship],
        decision: EntityResolutionDecision,
    ) -> bool:
        ...

    def complete_run(
        self,
        *,
        run_id: str,
        status: str,
        completed_at: datetime,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        ...


@dataclass(frozen=True)
class Phase2BatchResult:
    run_id: str
    request_key: str
    input_count: int
    decision_count: int
    matched_count: int
    research_required_count: int
    provider_error_count: int


class Phase2BatchExecutor:
    """Orchestrate Phase 2 without embedding provider-specific research policy."""

    def __init__(
        self,
        phase1_repository: Phase1HandoffSource,
        phase2_repository: Phase2Persistence,
    ) -> None:
        self._phase1_repository = phase1_repository
        self._phase2_repository = phase2_repository

    def run(
        self,
        *,
        request_key: str,
        candidate_provider: Phase2CandidateProvider
        | Callable[[Phase1Handoff], Phase2CandidateSet],
        limit: int | None = None,
        candidate_budget: int = 25,
        now: datetime | None = None,
    ) -> Phase2BatchResult:
        if not request_key.strip():
            raise ValueError("request_key must not be empty")
        if limit is not None and limit < 1:
            raise ValueError("limit must be positive when provided")
        if candidate_budget < 1:
            raise ValueError("candidate_budget must be positive")

        started_at = now or datetime.now(UTC)
        handoffs = self._phase1_repository.list_handoffs(limit=limit)
        run = self._phase2_repository.create_run(
            Phase2RunRecord(
                run_id=str(uuid4()),
                request_key=request_key,
                contract_version=PHASE2_CONTRACT_VERSION,
                matching_version=MATCHING_VERSION,
                started_at=started_at,
                input_count=0,
                decision_count=0,
                candidate_count=0,
                escalation_count=0,
                metadata={
                    "executor": "phase2.batch.v1",
                    "candidate_budget": candidate_budget,
                    "input_limit": limit,
                    "provider": type(candidate_provider).__name__,
                },
            )
        )

        if run.status == "COMPLETED":
            return self._completed_result(run)
        if run.status != "RUNNING":
            raise RuntimeError(
                f"phase2 request_key {request_key!r} already maps to run status {run.status}"
            )

        matched_count = 0
        research_required_count = 0
        provider_error_count = 0
        decision_count = 0

        try:
            for handoff in handoffs:
                try:
                    candidate_set = self._discover(candidate_provider, handoff)
                except Exception:
                    # Provider failures are not negative entity evidence.
                    candidate_set = Phase2CandidateSet()
                    provider_error_count += 1

                decision = resolve_entity(
                    handoff,
                    list(candidate_set.candidates),
                    relationships=list(candidate_set.relationships),
                    now=started_at,
                    candidate_budget=candidate_budget,
                )
                self._phase2_repository.persist_resolution(
                    run_id=run.run_id,
                    lead_id=handoff.lead_id,
                    candidates=candidate_set.candidates,
                    comparisons=decision.comparisons,
                    relationships=decision.relationships,
                    decision=decision,
                )
                decision_count += 1
                if decision.status in {"MATCHED", "MATCHED_WITH_RELATIONSHIP"}:
                    matched_count += 1
                if decision.research_required:
                    research_required_count += 1
        except Exception as exc:
            self._phase2_repository.complete_run(
                run_id=run.run_id,
                status="FAILED",
                completed_at=datetime.now(UTC),
                metadata={
                    "executor": "phase2.batch.v1",
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:1000],
                    "provider_error_count": provider_error_count,
                },
            )
            raise

        completed_at = datetime.now(UTC)
        self._phase2_repository.complete_run(
            run_id=run.run_id,
            status="COMPLETED",
            completed_at=completed_at,
            metadata={
                "executor": "phase2.batch.v1",
                "provider_error_count": provider_error_count,
                "matched_count": matched_count,
                "research_required_count": research_required_count,
                "decision_count": decision_count,
            },
        )
        return Phase2BatchResult(
            run_id=run.run_id,
            request_key=request_key,
            input_count=len(handoffs),
            decision_count=decision_count,
            matched_count=matched_count,
            research_required_count=research_required_count,
            provider_error_count=provider_error_count,
        )

    @staticmethod
    def _discover(
        provider: Phase2CandidateProvider | Callable[[Phase1Handoff], Phase2CandidateSet],
        handoff: Phase1Handoff,
    ) -> Phase2CandidateSet:
        discover = getattr(provider, "discover", None)
        if discover is not None:
            return cast(Phase2CandidateProvider, provider).discover(handoff)
        return cast(Callable[[Phase1Handoff], Phase2CandidateSet], provider)(handoff)

    @staticmethod
    def _completed_result(run: Phase2RunRecord) -> Phase2BatchResult:
        metadata = run.metadata
        return Phase2BatchResult(
            run_id=run.run_id,
            request_key=run.request_key,
            input_count=run.input_count,
            decision_count=run.decision_count,
            matched_count=int(metadata.get("matched_count", 0)),
            research_required_count=int(metadata.get("research_required_count", 0)),
            provider_error_count=int(metadata.get("provider_error_count", 0)),
        )
