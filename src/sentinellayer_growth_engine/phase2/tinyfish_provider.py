from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime
from urllib.parse import urlparse

from ..phase1.models import Phase1Handoff
from ..provider_resilience import TinyFishRequestTelemetry
from ..tinyfish_client import TinyFishSearchResult
from .extraction import (
    EvidenceInput,
    GroqEntityEvidenceExtractor,
    extract_with_fallback,
)
from .models import Currentness, EntityCandidate, EntityType
from .observability import TinyFishAttemptRecorder
from .normalization import normalize_domain, normalize_name, registrable_domain
from .research import (
    ResearchMission,
    TinyFishFetchObservation,
    TinyFishResearchAdapter,
    TinyFishSearchObservation,
    TinyFishSearchRequest,
)
from .repository import Phase2Repository
from .storage import ResearchObservationRecord


_KNOWN_ENTITY_TYPES = {
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
}


class TinyFishTelemetryBuffer:
    """Collect provider telemetry so a run-bound recorder can persist it."""

    def __init__(self) -> None:
        self._events: list[TinyFishRequestTelemetry] = []

    def __call__(self, telemetry: TinyFishRequestTelemetry) -> None:
        self._events.append(telemetry)

    def drain(self) -> list[TinyFishRequestTelemetry]:
        events = list(self._events)
        self._events.clear()
        return events


class TinyFishEntityCandidateProvider:
    """Turn bounded TinyFish evidence into research-origin candidate objects.

    Search/Fetch and semantic extraction remain observation-only. This provider
    never assigns an EntityResolutionDecision.
    """

    def __init__(
        self,
        adapter: TinyFishResearchAdapter,
        repository: Phase2Repository,
        telemetry_buffer: TinyFishTelemetryBuffer,
        *,
        groq_extractor: GroqEntityEvidenceExtractor | None = None,
        max_search_results: int = 5,
        max_fetch_urls: int = 3,
    ) -> None:
        if max_search_results < 1:
            raise ValueError("max_search_results must be positive")
        if max_fetch_urls < 1 or max_fetch_urls > 10:
            raise ValueError("max_fetch_urls must be between 1 and 10")
        self._adapter = adapter
        self._repository = repository
        self._telemetry_buffer = telemetry_buffer
        self._groq_extractor = groq_extractor
        self._max_search_results = max_search_results
        self._max_fetch_urls = max_fetch_urls
        self._run_id: str | None = None

    def bind_run(self, run_id: str) -> None:
        if not run_id.strip():
            raise ValueError("run_id must not be empty")
        self._run_id = run_id

    def discover(self, handoff: Phase1Handoff) -> object:
        if self._run_id is None:
            raise RuntimeError("TinyFishEntityCandidateProvider must be bound to a Phase 2 run")

        lead = handoff.canonical_lead
        mission = ResearchMission(
            mission_id=f"{handoff.lead_id}:entity_identity",
            lead_id=handoff.lead_id,
            mission_type="entity_identity",
            objective=(
                "Determine which real-world organization is represented by the supplied "
                "company/domain and distinguish the target identity from related parent, "
                "brand, subsidiary, vendor, and operating entities."
            ),
            required_evidence=("official_identity", "entity_type", "currentness"),
        )
        query_subject = lead.legal_name or lead.display_name or lead.domain or handoff.lead_id
        request = TinyFishSearchRequest(
            query=f'"{query_subject}" company organization',
            purpose=(
                "Determine whether the supplied company/domain resolves to this organization "
                "and identify an evidence-backed current entity type."
            ),
            location=lead.country_code,
            include_domains=(lead.domain,) if lead.domain else (),
            page=0,
        )
        search_request_id = self._internal_request_id("search", handoff.lead_id, request.params())
        try:
            search_observations = self._adapter.search(
                mission,
                request,
                provider_request_id=search_request_id,
            )
        finally:
            self._persist_telemetry(
                handoff,
                mission,
                operation="search",
                request_parameters=request.params(),
                result_count=None,
            )

        self._persist_search_observations(handoff, mission, search_observations)
        selected_urls = self._select_fetch_urls(lead.domain, search_observations)
        if not selected_urls:
            return _candidate_set(())

        fetch_purpose = (
            "Inspect the selected official source for explicit organization identity, "
            "entity type, and currentness evidence."
        )
        fetch_request_id = self._internal_request_id(
            "fetch",
            handoff.lead_id,
            {"urls": selected_urls, "purpose": fetch_purpose},
        )
        try:
            fetch_observations = self._adapter.fetch(
                mission,
                selected_urls,
                provider_request_id=fetch_request_id,
                purpose=fetch_purpose,
                ttl=0,
            )
        finally:
            self._persist_telemetry(
                handoff,
                mission,
                operation="fetch",
                request_parameters={
                    "urls": selected_urls,
                    "purpose": fetch_purpose,
                    "format": "markdown",
                    "links": False,
                    "image_links": False,
                    "page_metadata": True,
                    "ttl": 0,
                },
                result_count=None,
            )

        self._persist_fetch_observations(handoff, mission, fetch_observations)
        evidence = self._evidence_inputs(fetch_observations)
        if not evidence:
            return _candidate_set(())

        extracted, _mode = extract_with_fallback(
            extractor=self._groq_extractor,
            lead=handoff,
            evidence=evidence,
        )
        return _candidate_set(self._candidate_objects(handoff, extracted, evidence))

    def _persist_search_observations(
        self,
        handoff: Phase1Handoff,
        mission: ResearchMission,
        observations: Sequence[TinyFishSearchObservation],
    ) -> None:
        assert self._run_id is not None
        for observation in observations:
            observation_id = self._stable_id(
                "search",
                self._run_id,
                mission.mission_id,
                str(observation.result_position),
                observation.url,
            )
            self._repository.persist_research_observation(
                ResearchObservationRecord(
                    run_id=self._run_id,
                    observation_id=observation_id,
                    mission_id=mission.mission_id,
                    provider=observation.provider,
                    observation_type="SEARCH_RESULT",
                    result_position=observation.result_position,
                    url=observation.url,
                    source_domain=observation.source_domain,
                    title=observation.title,
                    snippet=observation.snippet,
                    observed_at=observation.observed_at,
                    request_params=observation.request_parameters,
                    provenance={
                        "provider_request_id": observation.provider_request_id,
                        "query": observation.query,
                        "lead_id": handoff.lead_id,
                    },
                    observation_payload={
                        "provider_request_id": observation.provider_request_id,
                        "title": observation.title,
                        "url": observation.url,
                        "snippet": observation.snippet,
                        "source_domain": observation.source_domain,
                    },
                )
            )

    def _persist_fetch_observations(
        self,
        handoff: Phase1Handoff,
        mission: ResearchMission,
        observations: Sequence[TinyFishFetchObservation],
    ) -> None:
        assert self._run_id is not None
        for index, observation in enumerate(observations):
            observation_id = self._stable_id(
                "fetch",
                self._run_id,
                mission.mission_id,
                str(index),
                observation.url,
            )
            published_at = _parse_published_at(observation.published_at)
            self._repository.persist_research_observation(
                ResearchObservationRecord(
                    run_id=self._run_id,
                    observation_id=observation_id,
                    mission_id=mission.mission_id,
                    provider=observation.provider,
                    observation_type="FETCH_RESULT",
                    result_position=index,
                    url=observation.url,
                    final_url=observation.final_url,
                    source_domain=(urlparse(observation.final_url or observation.url).hostname or "").lower(),
                    title=observation.title,
                    text_content=observation.text,
                    published_at=published_at,
                    observed_at=observation.fetched_at,
                    request_params={
                        "purpose": "Inspect the selected official source for explicit organization identity, entity type, and currentness evidence.",
                        "format": "markdown",
                        "links": False,
                        "image_links": False,
                        "page_metadata": True,
                        "ttl": 0,
                    },
                    provenance={
                        "provider_request_id": observation.provider_request_id,
                        "search_linked": observation.search_linked,
                        "lead_id": handoff.lead_id,
                    },
                    search_linked=observation.search_linked,
                    observation_payload={
                        "provider_request_id": observation.provider_request_id,
                        "url": observation.url,
                        "final_url": observation.final_url,
                        "title": observation.title,
                        "text": observation.text,
                        "published_at": observation.published_at,
                        "search_linked": observation.search_linked,
                    },
                )
            )

    def _persist_telemetry(
        self,
        handoff: Phase1Handoff,
        mission: ResearchMission,
        *,
        operation: str,
        request_parameters: dict[str, object],
        result_count: int | None,
    ) -> None:
        if self._run_id is None:
            return
        recorder = TinyFishAttemptRecorder(
            self._repository,
            run_id=self._run_id,
            lead_id=handoff.lead_id,
            mission_id=mission.mission_id,
        )
        for telemetry in self._telemetry_buffer.drain():
            recorder.record(
                telemetry,
                request_parameters=request_parameters,
                result_count=result_count,
                escalation_reason="phase2_entity_identity",
                information_gain_estimate=(
                    1.0 if telemetry.status == "SUCCEEDED" else 0.0
                ),
                metadata={"operation_context": operation},
            )

    @staticmethod
    def _select_fetch_urls(
        lead_domain: str | None,
        observations: Sequence[TinyFishSearchObservation],
    ) -> list[str]:
        target_registrable = registrable_domain(lead_domain)
        selected: list[str] = []
        for observation in observations:
            source_registrable = registrable_domain(observation.source_domain)
            if target_registrable and source_registrable != target_registrable:
                continue
            if observation.url not in selected:
                selected.append(observation.url)
            if len(selected) >= 3:
                break
        return selected

    @staticmethod
    def _evidence_inputs(
        observations: Sequence[TinyFishFetchObservation],
    ) -> list[EvidenceInput]:
        evidence: list[EvidenceInput] = []
        for index, observation in enumerate(observations):
            evidence.append(
                EvidenceInput(
                    evidence_id=TinyFishEntityCandidateProvider._stable_id(
                        "evidence",
                        observation.mission_id,
                        str(index),
                        observation.final_url or observation.url,
                    ),
                    url=observation.final_url or observation.url,
                    title=observation.title,
                    text=observation.text,
                )
            )
        return evidence

    @staticmethod
    def _candidate_objects(
        handoff: Phase1Handoff,
        extracted: object,
        evidence: Sequence[EvidenceInput],
    ) -> list[EntityCandidate]:
        lead = handoff.canonical_lead
        display_name = normalize_name(lead.display_name)
        legal_name = normalize_name(lead.legal_name)
        lead_domain = normalize_domain(lead.domain)

        evidence_by_id = {item.evidence_id: item for item in evidence}
        result: list[EntityCandidate] = []
        seen: set[str] = set()

        for extracted_candidate in extracted.candidate_entities:
            entity_type = extracted_candidate.entity_type.strip().upper()
            if entity_type not in _KNOWN_ENTITY_TYPES:
                continue

            candidate_domain = normalize_domain(extracted_candidate.domain)
            evidence_refs = [
                evidence_id
                for evidence_id in extracted_candidate.evidence_ids
                if evidence_id in evidence_by_id
            ]
            if not evidence_refs:
                continue

            supported_domains = {
                normalize_domain(urlparse(evidence_by_id[evidence_id].url).hostname)
                for evidence_id in evidence_refs
            }
            same_domain = bool(lead_domain and lead_domain in supported_domains)
            same_name = normalize_name(extracted_candidate.name) in {
                value for value in (display_name, legal_name) if value
            }
            domain_matches_candidate = bool(
                lead_domain and candidate_domain and candidate_domain == lead_domain
            )
            if not same_name and not domain_matches_candidate:
                continue

            effective_domain = candidate_domain or (lead.domain if same_domain else None)
            candidate_key = f"{normalize_name(extracted_candidate.name)}|{effective_domain}|{entity_type}"
            candidate_id = f"research:{self_hash(candidate_key)}"
            if candidate_id in seen:
                continue
            seen.add(candidate_id)

            official_url = next(
                (
                    item.url
                    for item in (evidence_by_id[evidence_id] for evidence_id in evidence_refs)
                    if normalize_domain(urlparse(item.url).hostname) == lead_domain
                ),
                evidence_by_id[evidence_refs[0]].url,
            )
            currentness = _currentness_for_name(
                extracted_candidate.name,
                extracted.currentness_claims,
            )
            result.append(
                EntityCandidate(
                    candidate_id=candidate_id,
                    entity_id=f"entity:{self_hash(candidate_key)}",
                    entity_type=entity_type,  # type: ignore[arg-type]
                    canonical_name=extracted_candidate.name,
                    canonical_domain=effective_domain,
                    official_url=official_url,
                    domain_verified=same_domain,
                    official_corporate_url_match=same_domain,
                    explicit_official_identity_tie=same_domain and same_name,
                    currentness=currentness,
                    evidence_refs=evidence_refs,
                    origin="research",
                )
            )
        return result

    @staticmethod
    def _internal_request_id(
        operation: str,
        lead_id: str,
        params: dict[str, str] | dict[str, object],
    ) -> str:
        return f"client:{operation}:{self_hash(lead_id + '|' + repr(sorted(params.items())))}"

    @staticmethod
    def _stable_id(*parts: str) -> str:
        return self_hash("|".join(parts))


def _candidate_set(candidates: Sequence[EntityCandidate]) -> object:
    # Imported lazily to keep this provider module free of execution dependencies.
    from .execution import Phase2CandidateSet

    return Phase2CandidateSet(candidates=tuple(candidates))


def _currentness_for_name(name: str, claims: Sequence[object]) -> Currentness:
    normalized = normalize_name(name)
    allowed: set[str] = {"CURRENT", "HISTORICAL", "UNKNOWN", "NOT_ESTABLISHED", "CONFLICT"}
    for claim in claims:
        claim_name = getattr(claim, "entity_name", "")
        if normalize_name(claim_name) == normalized:
            currentness = str(getattr(claim, "currentness", "UNKNOWN")).upper()
            if currentness in allowed:
                return currentness  # type: ignore[return-value]
    return "UNKNOWN"


def _parse_published_at(value: str | None) -> datetime | None:
    if not value:
        return None
    candidate = value.strip()
    try:
        if len(candidate) == 10:
            return datetime.fromisoformat(candidate).replace(tzinfo=UTC)
        return datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        return None


def self_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
