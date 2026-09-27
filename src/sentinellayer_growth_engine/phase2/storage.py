from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RunStatus = Literal["RUNNING", "COMPLETED", "FAILED", "CANCELLED"]
ProviderAttemptStatus = Literal[
    "STARTED", "SUCCEEDED", "FAILED", "RATE_LIMITED", "CACHED"
]
ResearchObservationType = Literal["SEARCH_RESULT", "FETCH_RESULT"]


class Phase2RunRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    request_key: str = Field(min_length=1, max_length=500)
    contract_version: str = Field(min_length=1, max_length=120)
    matching_version: str = Field(min_length=1, max_length=120)
    status: RunStatus = "RUNNING"
    started_at: datetime
    completed_at: datetime | None = None
    input_count: int = Field(default=0, ge=0)
    decision_count: int = Field(default=0, ge=0)
    candidate_count: int = Field(default=0, ge=0)
    escalation_count: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderAttemptRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    lead_id: str | None = None
    mission_id: str | None = None
    provider: str = Field(min_length=1, max_length=120)
    operation: str = Field(min_length=1, max_length=120)
    request_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    request_payload: dict[str, Any] = Field(default_factory=dict)
    status: ProviderAttemptStatus
    provider_request_id: str | None = None
    http_status: int | None = Field(default=None, ge=100, le=599)
    retry_count: int = Field(default=0, ge=0)
    result_count: int | None = Field(default=None, ge=0)
    latency_ms: int | None = Field(default=None, ge=0)
    cost_units: float | None = Field(default=None, ge=0)
    error_code: str | None = None
    error_message: str | None = None
    quota_state: dict[str, Any] = Field(default_factory=dict)
    raw_artifact_ref: str | None = None
    raw_artifact_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    evidence_ids: list[str] = Field(default_factory=list)
    escalation_reason: str | None = None
    information_gain_estimate: float | None = None
    started_at: datetime
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchObservationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    observation_id: str
    mission_id: str
    provider: str
    observation_type: ResearchObservationType
    result_position: int | None = Field(default=None, ge=0)
    url: str | None = None
    final_url: str | None = None
    source_domain: str | None = None
    title: str | None = None
    snippet: str | None = None
    text_content: str | None = None
    published_at: datetime | None = None
    observed_at: datetime
    request_params: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    search_linked: bool = False
    observation_payload: dict[str, Any]


class EvaluationResultRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    benchmark_version: str
    case_id: str
    entity_type_score: float | None = Field(default=None, ge=0, le=1)
    ownership_score: float | None = Field(default=None, ge=0, le=1)
    operating_entity_score: float | None = Field(default=None, ge=0, le=1)
    relationship_score: float | None = Field(default=None, ge=0, le=1)
    functional_control_score: float | None = Field(default=None, ge=0, le=1)
    currentness_score: float | None = Field(default=None, ge=0, le=1)
    evidence_quality_score: float | None = Field(default=None, ge=0, le=1)
    false_positive_safety_score: float | None = Field(default=None, ge=0, le=1)
    total_score: float | None = Field(default=None, ge=0)
    critical_failure: bool = False
    passed: bool
    expected_payload: dict[str, Any]
    observed_payload: dict[str, Any]
    evaluator_version: str
