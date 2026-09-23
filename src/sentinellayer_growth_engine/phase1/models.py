from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PHASE1_CONTRACT_VERSION = "v1"
NORMALIZATION_VERSION = "phase1.v1"

QualityStatus = Literal[
    "ACCEPTED",
    "ACCEPTED_WITH_WARNINGS",
    "QUARANTINED",
    "REJECTED",
    "DUPLICATE",
]
RecordState = Literal[
    "RECEIVED",
    "NORMALIZED",
    "VALIDATED",
    "ACCEPTED",
    "ACCEPTED_WITH_WARNINGS",
    "QUARANTINED",
    "REJECTED",
    "DUPLICATE",
]
FindingSeverity = Literal["ERROR", "WARNING", "INFO"]
ValueState = Literal["observed", "normalized", "missing", "invalid", "conflicting"]
DuplicateType = Literal["replay", "exact_duplicate", "not_duplicate"]

_HEX64 = r"^[a-f0-9]{64}$"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


class SourceFieldBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canonical_field: str = Field(min_length=1, max_length=120)
    source_field_name: str = Field(min_length=1, max_length=200)
    raw_value: Any = None


class LeadSourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["v1"] = "v1"
    source_record_id: str = Field(min_length=3, max_length=200)
    source_name: str = Field(min_length=1, max_length=120)
    source_version: str | None = Field(default=None, max_length=120)
    source_record_key: str | None = Field(default=None, max_length=500)
    acquired_at: datetime
    source_payload: dict[str, Any] = Field(min_length=1)
    mapped_fields: list[SourceFieldBinding] = Field(default_factory=list)
    raw_fingerprint: str = Field(pattern=_HEX64)
    adapter_version: str = Field(min_length=1, max_length=120)

    _normalize_timestamp = field_validator("acquired_at")(_utc)


class FieldObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=3, max_length=200)
    lead_id: str = Field(min_length=3, max_length=200)
    source_record_id: str = Field(min_length=3, max_length=200)
    field: str = Field(min_length=1, max_length=120)
    source_field_name: str = Field(min_length=1, max_length=200)
    raw_value: Any = None
    normalized_value: Any = None
    value_state: ValueState
    observed_at: datetime
    adapter_version: str = Field(min_length=1, max_length=120)
    normalization_version: str = Field(min_length=1, max_length=120)
    transformation_reason: str = Field(min_length=1, max_length=500)

    _normalize_timestamp = field_validator("observed_at")(_utc)


class ValidationFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str = Field(min_length=3, max_length=200)
    source_record_id: str | None = Field(default=None, max_length=200)
    lead_id: str | None = Field(default=None, max_length=200)
    field: str | None = Field(default=None, max_length=120)
    rule_id: str = Field(min_length=1, max_length=160)
    severity: FindingSeverity
    code: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=1, max_length=2000)
    observed_value_ref: str | None = Field(default=None, max_length=500)
    created_at: datetime
    validation_version: str = Field(min_length=1, max_length=120)

    _normalize_timestamp = field_validator("created_at")(_utc)


class DuplicateDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str = Field(min_length=3, max_length=200)
    source_record_id: str = Field(min_length=3, max_length=200)
    duplicate_type: DuplicateType
    rule_id: str = Field(min_length=1, max_length=160)
    matched_source_record_ids: list[str] = Field(default_factory=list)
    comparison_keys: dict[str, Any] = Field(default_factory=dict)
    decided_at: datetime
    decision_version: str = Field(min_length=1, max_length=120)

    _normalize_timestamp = field_validator("decided_at")(_utc)


class CanonicalLead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["v1"] = "v1"
    lead_id: str = Field(min_length=3, max_length=200)
    display_name: str | None = Field(default=None, max_length=500)
    legal_name: str | None = Field(default=None, max_length=500)
    domain: str | None = Field(default=None, max_length=500)
    canonical_url: str | None = Field(default=None, max_length=2000)
    country_code: str | None = Field(default=None, max_length=8)
    region: str | None = Field(default=None, max_length=300)
    city: str | None = Field(default=None, max_length=300)
    postal_code: str | None = Field(default=None, max_length=40)
    platform: str | None = Field(default=None, max_length=200)
    source_refs: list[str] = Field(min_length=1)
    field_observations: list[FieldObservation] = Field(default_factory=list)
    normalization_version: str = Field(min_length=1, max_length=120)
    raw_fingerprint: str = Field(pattern=_HEX64)
    source_fingerprint: str = Field(pattern=_HEX64)
    canonical_fingerprint: str = Field(pattern=_HEX64)
    quality_status: QualityStatus
    quality_finding_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    _normalize_created = field_validator("created_at")(_utc)
    _normalize_updated = field_validator("updated_at")(_utc)


class Phase1Handoff(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["v1"] = "v1"
    lead_id: str = Field(min_length=3, max_length=200)
    canonical_lead: CanonicalLead
    source_refs: list[str] = Field(min_length=1)
    field_observations: list[FieldObservation] = Field(default_factory=list)
    quality_status: QualityStatus
    quality_findings: list[ValidationFinding] = Field(default_factory=list)
    normalization_version: str = Field(min_length=1, max_length=120)
    canonical_fingerprint: str = Field(pattern=_HEX64)
    contract_version: str = Field(min_length=1, max_length=120)
    downstream_eligible: bool
    completed_at: datetime

    _normalize_completed = field_validator("completed_at")(_utc)


class Phase1Result(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: RecordState
    source_record: LeadSourceRecord
    canonical_lead: CanonicalLead | None = None
    findings: list[ValidationFinding] = Field(default_factory=list)
    duplicate_decision: DuplicateDecision
    handoff: Phase1Handoff | None = None
