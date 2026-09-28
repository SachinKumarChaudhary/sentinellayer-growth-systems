from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from ..phase1.models import Phase1Handoff
from ..phase1.repository import Phase1Repository
from .models import (
    EntityCandidate,
    EntityRelationship,
    EntityResolutionDecision,
    MATCHING_VERSION,
    PHASE2_CONTRACT_VERSION,
)
from .repository import Phase2Repository
from .resolver import resolve_entity
from .storage import Phase2RunRecord


@dataclass(frozen=True)
class Phase2CandidateSet:
    candidates: Sequence[EntityCandidate] = ()
    relationships: Sequence[EntityRelationship] = ()


class Phase2CandidateProvider(Protocol):
    def discover(self, handoff: Phase1Handoff) -> Phase2CandidateSet:
        """Return bounded candidate/evidence-derived inputs; never a final decision."""


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
        phase1_repository: Phase1Repository,
        phase2_repository: Phase2Repository,
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
                    "provider": getattr(candidate_provider, "__class__", type(candidate_provider)).__name__,
                },
            )
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
        discover = provider.discover if hasattr(provider, "discover") else provider
        return discover(handoff)
