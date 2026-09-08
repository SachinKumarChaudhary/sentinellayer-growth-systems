from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Channel = Literal["email", "phone", "linkedin", "instagram", "reddit", "x", "other"]
CompanyContactChannel = Literal["email", "phone", "contact_form", "other"]

BANNED_EVIDENCE_LABELS = ("VERIFIED", "INFERRED", "NOT_FOUND")


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_type: str = Field(min_length=1, max_length=120)
    claim: dict[str, Any]
    source_url: str | None = None
    source_type: str | None = None
    observed_at: datetime | None = None
    event_date: date | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("claim_type")
    @classmethod
    def claim_type_is_safe(cls, value: str) -> str:
        if any(label in value.upper() for label in BANNED_EVIDENCE_LABELS):
            raise ValueError("evidence labels are assigned by validation, not by the research agent")
        return value


class ContactMethod(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: Channel
    value: str = Field(min_length=1, max_length=2000)
    normalized_value: str = Field(min_length=1, max_length=2000)
    source: str | None = None
    source_url: str | None = None
    verification_status: Literal["unknown", "candidate"] = "unknown"
    verification_provider: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    first_seen_at: datetime | None = None
    last_verified_at: datetime | None = None

    @field_validator("value", "normalized_value", "source", "source_url", "verification_provider")
    @classmethod
    def no_banned_labels(cls, value: str | None) -> str | None:
        if value is not None and any(label in value.upper() for label in BANNED_EVIDENCE_LABELS):
            raise ValueError("verification labels are assigned by the validation pipeline")
        return value


class DecisionMaker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1, max_length=300)
    title: str | None = Field(default=None, max_length=300)
    role_family: str | None = Field(default=None, max_length=120)
    role_priority: int | None = Field(default=None, ge=1)
    rationale: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    contacts: list[ContactMethod] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)

    @field_validator("full_name", "title", "role_family", "rationale")
    @classmethod
    def text_is_safe(cls, value: str | None) -> str | None:
        if value is not None and any(label in value.upper() for label in BANNED_EVIDENCE_LABELS):
            raise ValueError("verification labels are assigned by the validation pipeline")
        return value


class CompanyContact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: CompanyContactChannel
    value: str = Field(min_length=1, max_length=2000)
    normalized_value: str = Field(min_length=1, max_length=2000)
    label: str | None = Field(default=None, max_length=120)
    source: str | None = None
    source_url: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence: list[Evidence] = Field(default_factory=list)


class IntentSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_type: str = Field(min_length=1, max_length=120)
    signal_date: date
    weight: float
    half_life_days: int = Field(gt=0)
    confidence: float | None = Field(default=None, ge=0, le=1)
    evidence: list[Evidence] = Field(default_factory=list)

    @field_validator("signal_type")
    @classmethod
    def signal_type_is_safe(cls, value: str) -> str:
        if any(label in value.upper() for label in BANNED_EVIDENCE_LABELS):
            raise ValueError("verification labels are assigned by the validation pipeline")
        return value


class CompanyFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_count: int | None = Field(default=None, ge=0)
    monthly_sessions: int | None = Field(default=None, ge=0)
    has_login: bool = False
    vertical: str | None = None
    ownership_type: str | None = None
    india_bridge: bool = False
    data_sensitivity: str | None = None


class EnrichmentPacket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    company_id: int = Field(gt=0)
    domain: str = Field(min_length=1, max_length=500)
    merchant_name: str | None = Field(default=None, max_length=500)
    company_facts: CompanyFacts = Field(default_factory=CompanyFacts)

    company_contacts: list[CompanyContact] = Field(default_factory=list)
    decision_makers: list[DecisionMaker] = Field(default_factory=list)
    intent_signals: list[IntentSignal] = Field(default_factory=list)

    personalization_angle: str | None = None
    research_notes: list[str] = Field(default_factory=list)

    @field_validator("personalization_angle")
    @classmethod
    def personalization_is_safe(cls, value: str | None) -> str | None:
        if value is not None and any(label in value.upper() for label in BANNED_EVIDENCE_LABELS):
            raise ValueError("verification labels are assigned by the validation pipeline")
        return value


class EnrichmentBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    packets: list[EnrichmentPacket] = Field(min_length=1, max_length=3)

    @field_validator("packets")
    @classmethod
    def companies_must_be_unique(cls, value: list[EnrichmentPacket]) -> list[EnrichmentPacket]:
        ids = [packet.company_id for packet in value]
        if len(ids) != len(set(ids)):
            raise ValueError("a batch cannot contain duplicate company_id values")
        return value
