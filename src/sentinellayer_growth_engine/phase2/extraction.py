from __future__ import annotations

import json
import os
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field

from ..phase1.models import Phase1Handoff


class GroqExtractionError(RuntimeError):
    """Raised when optional semantic evidence extraction cannot be completed safely."""


class EvidenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1, max_length=300)
    url: str = Field(min_length=1, max_length=2000)
    title: str | None = Field(default=None, max_length=1000)
    text: str = Field(min_length=1)


class EvidenceSpan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1, max_length=300)
    quote: str = Field(min_length=1, max_length=1500)


class CandidateEntityExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=500)
    entity_type: str = Field(min_length=1, max_length=120)
    domain: str | None = Field(default=None, max_length=500)
    relationship_to_target: str | None = Field(default=None, max_length=200)
    evidence_ids: list[str] = Field(default_factory=list)


class RelationshipClaimExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_name: str = Field(min_length=1, max_length=500)
    predicate: str = Field(min_length=1, max_length=120)
    object_name: str = Field(min_length=1, max_length=500)
    currentness: str = Field(min_length=1, max_length=80)
    evidence_ids: list[str] = Field(default_factory=list)


class CurrentnessClaimExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entity_name: str = Field(min_length=1, max_length=500)
    currentness: str = Field(min_length=1, max_length=80)
    evidence_ids: list[str] = Field(default_factory=list)


class ConflictExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=1500)
    evidence_ids: list[str] = Field(default_factory=list)


class EntityEvidenceExtraction(BaseModel):
    """Structured extraction only; it deliberately contains no final decision fields."""

    model_config = ConfigDict(extra="forbid")

    candidate_entities: list[CandidateEntityExtraction] = Field(default_factory=list)
    relationship_claims: list[RelationshipClaimExtraction] = Field(default_factory=list)
    currentness_claims: list[CurrentnessClaimExtraction] = Field(default_factory=list)
    conflicts: list[ConflictExtraction] = Field(default_factory=list)
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list)


@dataclass(frozen=True)
class GroqEntityEvidenceExtractor:
    """Optional semantic extraction boundary for already-collected evidence."""

    api_key: str
    model: str = "openai/gpt-oss-20b"
    endpoint: str = "https://api.groq.com/openai/v1/chat/completions"
    timeout_seconds: float = 20.0
    max_attempts: int = 3
    max_evidence_chars: int = 16000

    def extract(
        self,
        *,
        lead: Phase1Handoff,
        evidence: Sequence[EvidenceInput],
    ) -> EntityEvidenceExtraction:
        if not self.api_key.strip():
            raise ValueError("api_key must not be empty")
        if not evidence:
            raise ValueError("evidence must not be empty")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        if self.max_evidence_chars < 2000:
            raise ValueError("max_evidence_chars must be at least 2000")

        bounded_evidence = self._bound_evidence(evidence)

        payload = {
            "model": self.model,
            "temperature": 0,
            "top_p": 1,
            "stream": False,
            "n": 1,
            "max_completion_tokens": int(os.getenv("GROQ_MAX_COMPLETION_TOKENS", "2048")),
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Extract only evidence-supported organizational entity facts from the supplied "
                        "documents. Do not decide the final canonical entity. Do not emit canonical IDs, "
                        "MATCHED/AMBIGUOUS/CONFLICT/UNRESOLVED/NO_MATCH states, buyer roles, or scores. "
                        "Every claim must reference one or more evidence_id values. Never invent a name, "
                        "relationship, currentness state, or domain."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "lead": {
                                "lead_id": lead.lead_id,
                                "display_name": lead.canonical_lead.display_name,
                                "legal_name": lead.canonical_lead.legal_name,
                                "domain": lead.canonical_lead.domain,
                                "country_code": lead.canonical_lead.country_code,
                            },
                            "evidence": [item.model_dump(mode="json") for item in bounded_evidence],
                        }
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "entity_evidence_extraction",
                    "strict": True,
                    "schema": self.schema(),
                },
            },
        }

        data = json.dumps(payload).encode("utf-8")
        last_error: Exception | None = None

        for attempt in range(self.max_attempts):
            request = Request(
                self.endpoint,
                data=data,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "sentinellayer-growth-engine/0.1.0",
                },
            )
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    raw = response.read().decode("utf-8")
                envelope = json.loads(raw)
                content = envelope["choices"][0]["message"]["content"]
                parsed = EntityEvidenceExtraction.model_validate_json(content)
                self._validate_evidence_refs(parsed, evidence)
                return parsed
            except HTTPError as exc:
                last_error = exc
                if not self._retryable_status(exc.code):
                    raise GroqExtractionError(
                        f"Groq extraction rejected with HTTP {exc.code}"
                    ) from exc
            except (URLError, TimeoutError, OSError, KeyError, IndexError, TypeError, ValueError) as exc:
                last_error = exc

            if attempt + 1 < self.max_attempts:
                time.sleep(0.5 * (2**attempt))

        raise GroqExtractionError("Groq evidence extraction unavailable after bounded retries") from last_error

    def _bound_evidence(
        self,
        evidence: Sequence[EvidenceInput],
    ) -> tuple[EvidenceInput, ...]:
        remaining_chars = self.max_evidence_chars
        bounded: list[EvidenceInput] = []
        items = list(evidence)

        for index, item in enumerate(items):
            if remaining_chars <= 0:
                break
            items_remaining = len(items) - index
            per_item_budget = max(1, remaining_chars // items_remaining)
            clipped_text = self._clip_text(item.text, per_item_budget)
            bounded.append(item.model_copy(update={"text": clipped_text}))
            remaining_chars -= len(clipped_text)

        return tuple(bounded)

    @staticmethod
    def _clip_text(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text

        marker = "\n...[TRUNCATED_FOR_SEMANTIC_EXTRACTION]...\n"
        if limit <= len(marker) + 2:
            return text[:limit]

        available = limit - len(marker)
        head_chars = max(1, int(available * 0.65))
        tail_chars = max(1, available - head_chars)
        return f"{text[:head_chars]}{marker}{text[-tail_chars:]}"

    @staticmethod
    def _retryable_status(status: int) -> bool:
        return status in {408, 409, 429} or status >= 500

    @staticmethod
    def _validate_evidence_refs(
        result: EntityEvidenceExtraction,
        evidence: Sequence[EvidenceInput],
    ) -> None:
        valid_ids = {item.evidence_id for item in evidence}
        referenced: list[str] = []
        for candidate_item in result.candidate_entities:
            referenced.extend(candidate_item.evidence_ids)
        for relationship_item in result.relationship_claims:
            referenced.extend(relationship_item.evidence_ids)
        for currentness_item in result.currentness_claims:
            referenced.extend(currentness_item.evidence_ids)
        for conflict_item in result.conflicts:
            referenced.extend(conflict_item.evidence_ids)
        referenced.extend(span_item.evidence_id for span_item in result.evidence_spans)
        invalid = sorted(set(referenced) - valid_ids)
        if invalid:
            raise GroqExtractionError(
                f"Groq returned unknown evidence ids: {', '.join(invalid)}"
            )

    @staticmethod
    def schema() -> dict[str, Any]:
        return cast(
            dict[str, Any],
            {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "candidate_entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "name": {"type": "string"},
                                "entity_type": {"type": "string"},
                                "domain": {"type": ["string", "null"]},
                                "relationship_to_target": {"type": ["string", "null"]},
                                "evidence_ids": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": [
                                "name",
                                "entity_type",
                                "domain",
                                "relationship_to_target",
                                "evidence_ids",
                            ],
                        },
                    },
                    "relationship_claims": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "subject_name": {"type": "string"},
                                "predicate": {"type": "string"},
                                "object_name": {"type": "string"},
                                "currentness": {"type": "string"},
                                "evidence_ids": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": [
                                "subject_name",
                                "predicate",
                                "object_name",
                                "currentness",
                                "evidence_ids",
                            ],
                        },
                    },
                    "currentness_claims": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "entity_name": {"type": "string"},
                                "currentness": {"type": "string"},
                                "evidence_ids": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["entity_name", "currentness", "evidence_ids"],
                        },
                    },
                    "conflicts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "description": {"type": "string"},
                                "evidence_ids": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["description", "evidence_ids"],
                        },
                    },
                    "evidence_spans": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "evidence_id": {"type": "string"},
                                "quote": {"type": "string"},
                            },
                            "required": ["evidence_id", "quote"],
                        },
                    },
                },
                "required": [
                    "candidate_entities",
                    "relationship_claims",
                    "currentness_claims",
                    "conflicts",
                    "evidence_spans",
                ],
            },
        )


_RELATION_PATTERNS = (
    ("operated by", "OPERATED_BY", "OPERATING_ENTITY"),
    ("owned by", "OWNED_BY", "UNKNOWN"),
    ("a subsidiary of", "SUBSIDIARY_OF", "UNKNOWN"),
    ("subsidiary of", "SUBSIDIARY_OF", "UNKNOWN"),
    ("a brand of", "BRAND_OF", "UNKNOWN"),
    ("brand of", "BRAND_OF", "UNKNOWN"),
    ("part of", "PART_OF", "UNKNOWN"),
    ("acquired by", "ACQUIRED_BY", "UNKNOWN"),
)


def deterministic_extract_evidence(
    *,
    lead: Phase1Handoff,
    evidence: Sequence[EvidenceInput],
) -> EntityEvidenceExtraction:
    """Conservative regex extraction used when Groq is unavailable or malformed."""

    candidates: list[CandidateEntityExtraction] = []
    relationships: list[RelationshipClaimExtraction] = []
    spans: list[EvidenceSpan] = []

    for item in evidence:
        text = " ".join(part for part in (item.title or "", item.text) if part)
        for phrase, predicate, entity_type in _RELATION_PATTERNS:
            pattern = re.compile(
                rf"\b{re.escape(phrase)}\s+([A-Z][A-Za-z0-9&'.,-]*(?:\s+[A-Z][A-Za-z0-9&'.,-]*){{0,6}})"
            )
            match = pattern.search(text)
            if not match:
                continue
            name = match.group(1).rstrip(".,;:")
            if not name:
                continue

            candidates.append(
                CandidateEntityExtraction(
                    name=name,
                    entity_type=entity_type,
                    relationship_to_target=predicate,
                    evidence_ids=[item.evidence_id],
                )
            )
            relationships.append(
                RelationshipClaimExtraction(
                    subject_name=lead.canonical_lead.display_name
                    or lead.canonical_lead.legal_name
                    or lead.lead_id,
                    predicate=predicate,
                    object_name=name,
                    currentness="UNKNOWN",
                    evidence_ids=[item.evidence_id],
                )
            )
            quote = match.group(0).strip()
            spans.append(EvidenceSpan(evidence_id=item.evidence_id, quote=quote[:1500]))

    return EntityEvidenceExtraction(
        candidate_entities=_dedupe_candidates(candidates),
        relationship_claims=_dedupe_relationships(relationships),
        evidence_spans=_dedupe_spans(spans),
    )


def extract_with_fallback(
    *,
    extractor: GroqEntityEvidenceExtractor | None,
    lead: Phase1Handoff,
    evidence: Sequence[EvidenceInput],
) -> tuple[EntityEvidenceExtraction, str]:
    if extractor is None:
        return deterministic_extract_evidence(lead=lead, evidence=evidence), "deterministic"

    try:
        return extractor.extract(lead=lead, evidence=evidence), "groq"
    except (GroqExtractionError, OSError, TimeoutError, ValueError):
        return deterministic_extract_evidence(lead=lead, evidence=evidence), "deterministic"


def _dedupe_candidates(
    items: list[CandidateEntityExtraction],
) -> list[CandidateEntityExtraction]:
    seen: set[tuple[str, str, str | None]] = set()
    result: list[CandidateEntityExtraction] = []
    for item in items:
        key = (item.name.casefold(), item.entity_type, item.domain)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _dedupe_relationships(
    items: list[RelationshipClaimExtraction],
) -> list[RelationshipClaimExtraction]:
    seen: set[tuple[str, str, str]] = set()
    result: list[RelationshipClaimExtraction] = []
    for item in items:
        key = (item.subject_name.casefold(), item.predicate, item.object_name.casefold())
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _dedupe_spans(items: list[EvidenceSpan]) -> list[EvidenceSpan]:
    seen: set[tuple[str, str]] = set()
    result: list[EvidenceSpan] = []
    for item in items:
        key = (item.evidence_id, item.quote)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
