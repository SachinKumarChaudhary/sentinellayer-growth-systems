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
from .resolver import resolve_entity

__all__ = [
    "EntityCandidate",
    "EntityComparison",
    "EntityRelationship",
    "EntityResolutionDecision",
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
