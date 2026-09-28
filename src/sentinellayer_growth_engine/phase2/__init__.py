"""Phase 2: deterministic-first entity resolution."""

from .blocking import generate_candidates
from .execution import (
    Phase2BatchExecutor,
    Phase2BatchResult,
    Phase2CandidateSet,
    Phase2ProviderUnavailable,
)
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
from .observability import TinyFishAttemptRecorder
from .repository import Phase2Repository
from .research import (
    ResearchMission,
    TinyFishFetchObservation,
    TinyFishResearchAdapter,
    TinyFishSearchObservation,
    TinyFishSearchRequest,
    candidate_from_research,
)
from .resolver import resolve_entity
from .storage import (
    EvaluationResultRecord,
    Phase2RunRecord,
    ProviderAttemptRecord,
    ResearchObservationRecord,
)
from .tinyfish_provider import TinyFishEntityCandidateProvider, TinyFishTelemetryBuffer

__all__ = [
    "CandidateEntityExtraction",
    "CurrentnessClaimExtraction",
    "EntityCandidate",
    "EntityComparison",
    "EntityEvidenceExtraction",
    "EntityRelationship",
    "EntityResolutionDecision",
    "EvaluationResultRecord",
    "EvidenceInput",
    "EvidenceSpan",
    "GroqEntityEvidenceExtractor",
    "GroqExtractionError",
    "Phase2BatchExecutor",
    "Phase2BatchResult",
    "Phase2CandidateSet",
    "Phase2ProviderUnavailable",
    "Phase2Repository",
    "Phase2RunRecord",
    "ProviderAttemptRecord",
    "RelationshipClaimExtraction",
    "ResearchMission",
    "ResearchObservationRecord",
    "TinyFishAttemptRecorder",
    "TinyFishEntityCandidateProvider",
    "TinyFishFetchObservation",
    "TinyFishResearchAdapter",
    "TinyFishSearchObservation",
    "TinyFishSearchRequest",
    "TinyFishTelemetryBuffer",
    "candidate_from_research",
    "compare_candidate",
    "deterministic_extract_evidence",
    "extract_with_fallback",
    "generate_candidates",
    "resolve_entity",
]
