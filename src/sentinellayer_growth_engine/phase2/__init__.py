"""Phase 2: deterministic-first entity resolution."""

from .blocking import generate_candidates
from .execution import Phase2BatchExecutor, Phase2BatchResult, Phase2CandidateSet
from .extraction import (
    CandidateEntityExtraction,
    CurrentnessClaimExtraction,
    EntityEvidenceExtraction,
    EvidenceInput,
    EvidenceSpan,
    GroqEntityEvidenceExtractor,
    GroqExtractionError,
    RelationshipClaimExtraction,
    deterministic_extract_evidence,
    extract_with_fallback,
)
from .matching import compare_candidate
from .models import (
    EntityCandidate,
    EntityComparison,
    EntityRelationship,
    EntityResolutionDecision,
)
from .tinyfish_provider import TinyFishEntityCandidateProvider, TinyFishTelemetryBuffer
from .research import (
    ResearchMission,
    TinyFishFetchObservation,
    TinyFishResearchAdapter,
    TinyFishSearchObservation,
    TinyFishSearchRequest,
    candidate_from_research,
)
from .observability import TinyFishAttemptRecorder
from .repository import Phase2Repository
from .resolver import resolve_entity
from .storage import (
    EvaluationResultRecord,
    Phase2RunRecord,
    ProviderAttemptRecord,
    ResearchObservationRecord,
)

__all__ = [
    "CandidateEntityExtraction",
    "CurrentnessClaimExtraction",
    "EntityCandidate",
    "EntityEvidenceExtraction",
    "Phase2BatchExecutor",
    "Phase2BatchResult",
    "Phase2CandidateSet",
    "EntityComparison",
    "EntityRelationship",
    "EntityResolutionDecision",
    "EvaluationResultRecord",
    "EvidenceInput",
    "EvidenceSpan",
    "Phase2Repository",
    "Phase2RunRecord",
    "ProviderAttemptRecord",
    "ResearchMission",
    "RelationshipClaimExtraction",
    "ResearchObservationRecord",
    "TinyFishAttemptRecorder",
    "TinyFishEntityCandidateProvider",
    "TinyFishTelemetryBuffer",
    "TinyFishFetchObservation",
    "TinyFishResearchAdapter",
    "TinyFishSearchObservation",
    "GroqEntityEvidenceExtractor",
    "GroqExtractionError",
    "deterministic_extract_evidence",
    "extract_with_fallback",
    "TinyFishSearchRequest",
    "candidate_from_research",
    "compare_candidate",
    "generate_candidates",
    "resolve_entity",
]
