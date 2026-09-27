from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256

from sentinellayer_growth_engine.phase1.models import Phase1Handoff

from .blocking import generate_candidates
from .matching import STRONG_SIGNAL_CODES, compare_candidate
from .models import (
    Confidence,
    DecisionTraceEvent,
    EntityCandidate,
    EntityComparison,
    EntityRelationship,
    EntityResolutionDecision,
    ResolutionStatus,
)


def _decision_id(lead_id: str, comparisons: list[EntityComparison]) -> str:
    material = "|".join(f"{item.candidate_id}:{item.score}" for item in comparisons)
    digest = sha256(f"{lead_id}|{material}".encode("utf-8")).hexdigest()[:24]
    return f"erd:{lead_id}:{digest}"


def _event(step: str, detail: str, candidate_id: str | None = None) -> DecisionTraceEvent:
    return DecisionTraceEvent(step=step, detail=detail, candidate_id=candidate_id)


def _eligible(comparison: EntityComparison) -> bool:
    return comparison.eligible_for_match and not comparison.hard_negative


def resolve_entity(
    lead: Phase1Handoff,
    candidates: list[EntityCandidate],
    *,
    relationships: list[EntityRelationship] | None = None,
    now: datetime | None = None,
    candidate_budget: int = 25,
) -> EntityResolutionDecision:
    decided_at = now or datetime.now(UTC)
    selected = generate_candidates(lead, candidates, budget=candidate_budget)
    comparisons = sorted(
        (compare_candidate(lead, candidate) for candidate in selected),
        key=lambda item: (item.eligible_for_match, item.score, item.candidate_id),
        reverse=True,
    )

    trace: list[DecisionTraceEvent] = [
        _event(
            "candidate_generation",
            f"Selected {len(selected)} candidates with budget {candidate_budget}.",
        )
    ]
    rejected = [item.candidate_id for item in comparisons if item.hard_negative]

    if not comparisons:
        trace.append(_event("adjudication", "No deterministic candidates were generated."))
        return EntityResolutionDecision(
            decision_id=_decision_id(lead.lead_id, comparisons),
            lead_id=lead.lead_id,
            status="UNRESOLVED",
            decision_trace=trace,
            rejected_candidates=rejected,
            research_required=True,
            research_missions=["entity_identity"],
            unresolved_questions=["No candidate entity survived deterministic blocking."],
            decided_at=decided_at,
        )

    eligible = [item for item in comparisons if _eligible(item)]
    if not eligible:
        plausible = [item for item in comparisons if not item.hard_negative and item.score > 0]
        if plausible:
            trace.append(
                _event(
                    "adjudication",
                    "Plausible candidate evidence exists, but deterministic identity evidence is insufficient; returning AMBIGUOUS.",
                )
            )
            return EntityResolutionDecision(
                decision_id=_decision_id(lead.lead_id, comparisons),
                lead_id=lead.lead_id,
                status="AMBIGUOUS",
                comparisons=comparisons,
                decision_trace=trace,
                rejected_candidates=rejected,
                research_required=True,
                research_missions=["entity_identity"],
                unresolved_questions=[
                    "Plausible candidates exist, but no candidate has sufficient deterministic identity evidence."
                ],
                decided_at=decided_at,
            )

        trace.append(
            _event(
                "adjudication",
                "All candidates were rejected or lacked any positive identity evidence.",
            )
        )
        return EntityResolutionDecision(
            decision_id=_decision_id(lead.lead_id, comparisons),
            lead_id=lead.lead_id,
            status="NO_MATCH",
            comparisons=comparisons,
            decision_trace=trace,
            rejected_candidates=rejected,
            research_required=True,
            research_missions=["entity_identity"],
            unresolved_questions=["No candidate met the deterministic identity evidence requirements."],
            decided_at=decided_at,
        )

    top = eligible[0]
    second = eligible[1] if len(eligible) > 1 else None
    top_candidate = next(item for item in selected if item.candidate_id == top.candidate_id)
    top_strong = [
        signal.code
        for signal in top.signals
        if signal.code in STRONG_SIGNAL_CODES and signal.value
    ]

    strong_competitors = [
        item
        for item in eligible
        if item.candidate_id != top.candidate_id
        and any(signal.code in STRONG_SIGNAL_CODES and signal.value for signal in item.signals)
    ]
    if strong_competitors:
        trace.append(
            _event(
                "adjudication",
                "Multiple candidates have strong identity evidence; returning CONFLICT.",
            )
        )
        return EntityResolutionDecision(
            decision_id=_decision_id(lead.lead_id, comparisons),
            lead_id=lead.lead_id,
            status="CONFLICT",
            comparisons=comparisons,
            decision_trace=trace,
            rejected_candidates=rejected,
            research_required=True,
            research_missions=["entity_identity", "currentness"],
            unresolved_questions=["Multiple candidates have materially strong identity evidence."],
            decided_at=decided_at,
        )

    margin = top.score - second.score if second else None
    confidence: Confidence
    if top_strong:
        status: ResolutionStatus = (
            "MATCHED_WITH_RELATIONSHIP" if relationships else "MATCHED"
        )
        confidence = "high" if margin is None or margin >= 15 else "medium"
    elif second is not None and margin is not None and margin < 20:
        trace.append(_event("adjudication", "Top candidates are too close to safely merge."))
        return EntityResolutionDecision(
            decision_id=_decision_id(lead.lead_id, comparisons),
            lead_id=lead.lead_id,
            status="AMBIGUOUS",
            comparisons=comparisons,
            decision_trace=trace,
            rejected_candidates=rejected,
            research_required=True,
            research_missions=["entity_identity"],
            unresolved_questions=["Candidate separation is insufficient for deterministic matching."],
            decided_at=decided_at,
        )
    else:
        status = "MATCHED_WITH_RELATIONSHIP" if relationships else "MATCHED"
        confidence = "medium"

    trace.append(
        _event(
            "adjudication",
            f"Candidate {top.candidate_id} selected with score {top.score}.",
            top.candidate_id,
        )
    )

    evidence_refs = sorted(set(top_candidate.evidence_refs))
    return EntityResolutionDecision(
        decision_id=_decision_id(lead.lead_id, comparisons),
        lead_id=lead.lead_id,
        status=status,
        canonical_entity_id=top_candidate.entity_id or top_candidate.candidate_id,
        entity_type=top_candidate.entity_type,
        canonical_name=top_candidate.canonical_name,
        canonical_domain=top_candidate.canonical_domain,
        confidence=confidence,
        decisive_signals=top_strong
        or [
            signal.code
            for signal in top.signals
            if signal.strength == "medium" and signal.value
        ],
        rejected_candidates=rejected,
        comparisons=comparisons,
        decision_trace=trace,
        evidence_refs=evidence_refs,
        currentness=top_candidate.currentness,
        relationships=relationships or [],
        research_required=False,
        decided_at=decided_at,
    )
