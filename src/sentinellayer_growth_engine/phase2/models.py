from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PHASE2_CONTRACT_VERSION = "phase2.entity_resolution.v1"
MATCHING_VERSION = "phase2.deterministic_match.v1"

EntityType = Literal[
    "LEGAL_ENTITY",
    "OPERATING_ENTITY",
    "BRAND",
    "BUSINESS_UNIT",
    "PARENT_COMPANY",
    "HOLDING_COMPANY",
    "FRANCHISEE",
    "LICENSOR",
    "LICENSEE",
    "EXTERNAL_PROVIDER",
    "UNKNOWN",
]

ResolutionStatus = Literal[
    "MATCHED",
    "MATCHED_WITH_RELATIONSHIP",
    "AMBIGUOUS",
    "CONFLICT",
    "UNRESOLVED",
    "NO_MATCH",
]

Currentness = Literal[
    "CURRENT",
    "HISTORICAL",
    "UNKNOWN",
    "NOT_ESTABLISHED",
    "CONFLICT",
]

CandidateOrigin = Literal["phase1", "provider", "research", "gold"]

RelationshipType = Literal[
    "SAME_ENTITY_AS",
    "BRAND_OF",
    "SUBSIDIARY_OF",
    "OWNED_BY",
    "OPERATES",
    "BUSINESS_UNIT_OF",
    "PARENT_OF",
    "FRANCHISE_OF",
    "LICENSED_FROM",
    "LICENSED_TO",
    "PROVIDES_SERVICE_TO",
    "FUNCTIONALLY_CONTROLS",
    "FORMERLY_OWNED_BY",
    "ACQUIRED",
    "DIVESTED",
    "UNKNOWN_RELATIONSHIP",
]

RelationshipStatus = Literal["ESTABLISHED", "NOT_ESTABLISHED", "CONFLICT", "UNKNOWN"]


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC)


class EntityCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1, max_length=300)
    entity_id: str | None = Field(default=None, max_length=300)
    entity_type: EntityType
    canonical_name: str = Field(min_length=1, max_length=500)
    canonical_domain: str | None = Field(default=None, max_length=500)
    aliases: list[str] = Field(default_factory=list)
    geography: list[str] = Field(default_factory=list)
    legal_identifier: str | None = Field(default=None, max_length=300)
    official_url: str | None = Field(default=None, max_length=2000)
    domain_verified: bool = False
    official_corporate_url_match: bool = False
    explicit_official_identity_tie: bool = False
    registered_identity_match: bool = False
    corporate_social_match: bool = False
    parent_relationship_consistent: bool = False
    historical_only: bool = False
    clearly_different_legal_entity: bool = False
    conflicting_authoritative_domain: bool = False
    conflicting_geography: bool = False
    external_provider_relationship: bool = False
    currentness: Currentness = "UNKNOWN"
    evidence_refs: list[str] = Field(default_factory=list)
    origin: CandidateOrigin = "provider"


class ComparisonSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=120)
    strength: Literal["strong", "medium", "weak", "negative"]
    weight: int
    value: bool
    reason: str = Field(min_length=1, max_length=500)


class EntityComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1, max_length=300)
    score: int
    signals: list[ComparisonSignal] = Field(default_factory=list)
    hard_negative: bool = False
    eligible_for_match: bool = False


class EntityRelationship(BaseModel):
    model_config = ConfigDict(extra="forbid")

    relationship_id: str = Field(min_length=1, max_length=300)
    subject_entity_id: str = Field(min_length=1, max_length=300)
    predicate: RelationshipType
    object_entity_id: str = Field(min_length=1, max_length=300)
    function_scope: str | None = Field(default=None, max_length=300)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    currentness: Currentness = "UNKNOWN"
    evidence_refs: list[str] = Field(default_factory=list)
    status: RelationshipStatus
    adjudication_reason: str = Field(min_length=1, max_length=1000)

    _normalize_valid_from = field_validator("valid_from")(_utc)
    _normalize_valid_to = field_validator("valid_to")(_utc)


class DecisionTraceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step: str = Field(min_length=1, max_length=120)
    detail: str = Field(min_length=1, max_length=2000)
    candidate_id: str | None = Field(default=None, max_length=300)


class EntityResolutionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(min_length=1, max_length=300)
    contract_version: Literal["phase2.entity_resolution.v1"] = PHASE2_CONTRACT_VERSION
    lead_id: str = Field(min_length=1, max_length=300)
    status: ResolutionStatus
    canonical_entity_id: str | None = Field(default=None, max_length=300)
    entity_type: EntityType = "UNKNOWN"
    canonical_name: str | None = Field(default=None, max_length=500)
    canonical_domain: str | None = Field(default=None, max_length=500)
    confidence: Literal["high", "medium", "low", "unknown"] = "unknown"
    decisive_signals: list[str] = Field(default_factory=list)
    rejected_candidates: list[str] = Field(default_factory=list)
    comparisons: list[EntityComparison] = Field(default_factory=list)
    decision_trace: list[DecisionTraceEvent] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    currentness: Currentness = "UNKNOWN"
    relationships: list[EntityRelationship] = Field(default_factory=list)
    research_required: bool = False
    research_missions: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    matching_version: Literal["phase2.deterministic_match.v1"] = MATCHING_VERSION
    decided_at: datetime

    _normalize_decided_at = field_validator("decided_at")(_utc)
