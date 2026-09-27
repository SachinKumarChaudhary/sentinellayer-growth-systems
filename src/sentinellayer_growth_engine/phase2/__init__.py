"""Phase 2: deterministic-first entity resolution."""

from .blocking import generate_candidates
from .matching import compare_candidate
from .models import (
    EntityCandidate,
    EntityComparison,
    EntityRelationship,
    EntityResolutionDecision,
)
from .resolver import resolve_entity

__all__ = [
    "EntityCandidate",
    "EntityComparison",
    "EntityRelationship",
    "EntityResolutionDecision",
    "compare_candidate",
    "generate_candidates",
    "resolve_entity",
]
