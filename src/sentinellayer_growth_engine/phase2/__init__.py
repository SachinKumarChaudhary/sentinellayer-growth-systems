"""Phase 2: deterministic-first entity resolution."""

from .blocking import generate_candidates
from .matching import compare_candidate
from .models import (
    EntityCandidate,
    EntityComparison,
    EntityRelationship,
    EntityResolutionDecision,
)
from .research import (
    ResearchMission,
    TinyFishFetchObservation,
    TinyFishResearchAdapter,
    TinyFishSearchObservation,
    TinyFishSearchRequest,
    candidate_from_research,
)
from .repository import Phase2Repository
from .resolver import resolve_entity
from .storage import (
    EvaluationResultRecord,
    Phase2RunRecord,
    ProviderAttemptRecord,
    ResearchObservationRecord,
)

__all__ = [
    "EntityCandidate",
    "EntityComparison",
    "EntityRelationship",
    "EntityResolutionDecision",
    "EvaluationResultRecord",
    "Phase2Repository",
    "Phase2RunRecord",
    "ProviderAttemptRecord",
    "ResearchObservationRecord",
    "ResearchMission",
    "TinyFishFetchObservation",
    "TinyFishResearchAdapter",
    "TinyFishSearchObservation",
    "TinyFishSearchRequest",
    "candidate_from_research",
    "compare_candidate",
    "generate_candidates",
    "resolve_entity",
]
