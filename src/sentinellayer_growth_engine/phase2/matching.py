from __future__ import annotations

from difflib import SequenceMatcher

from sentinellayer_growth_engine.phase1.models import Phase1Handoff

from .models import ComparisonSignal, EntityCandidate, EntityComparison
from .normalization import geography_tokens, name_tokens, normalize_domain, normalize_name


STRONG_SIGNAL_CODES = {
    "exact_verified_canonical_domain",
    "exact_official_corporate_url",
    "explicit_official_identity_tie",
}

MEDIUM_SIGNAL_CODES = {
    "normalized_company_name",
    "geography_match",
    "registered_identity_match",
    "corporate_social_match",
    "parent_relationship_consistent",
}


def _lead_name(lead: Phase1Handoff) -> str:
    return lead.canonical_lead.legal_name or lead.canonical_lead.display_name or ""


def compare_candidate(lead: Phase1Handoff, candidate: EntityCandidate) -> EntityComparison:
    signals: list[ComparisonSignal] = []
    score = 0
    hard_negative = False

    lead_domain = normalize_domain(lead.canonical_lead.domain)
    candidate_domain = normalize_domain(candidate.canonical_domain)
    if lead_domain and candidate_domain and lead_domain == candidate_domain and candidate.domain_verified:
        signals.append(ComparisonSignal(
            code="exact_verified_canonical_domain",
            strength="strong",
            weight=100,
            value=True,
            reason="Candidate has the exact supplied domain and marks it as verified.",
        ))
        score += 100

    if candidate.official_corporate_url_match:
        signals.append(ComparisonSignal(
            code="exact_official_corporate_url",
            strength="strong",
            weight=95,
            value=True,
            reason="Candidate's official corporate URL is explicitly tied to the lead.",
        ))
        score += 95

    if candidate.explicit_official_identity_tie:
        signals.append(ComparisonSignal(
            code="explicit_official_identity_tie",
            strength="strong",
            weight=90,
            value=True,
            reason="Official evidence explicitly ties the supplied identity to the candidate.",
        ))
        score += 90

    lead_name = normalize_name(_lead_name(lead))
    candidate_name = normalize_name(candidate.canonical_name)
    if lead_name and candidate_name and lead_name == candidate_name:
        signals.append(ComparisonSignal(
            code="normalized_company_name",
            strength="medium",
            weight=55,
            value=True,
            reason="Normalized lead company/legal name matches candidate name.",
        ))
        score += 55

    lead_geo = geography_tokens(
        [lead.canonical_lead.country_code or "", lead.canonical_lead.region or "", lead.canonical_lead.city or ""]
    )
    candidate_geo = geography_tokens(candidate.geography)
    if lead_geo and candidate_geo and lead_geo.intersection(candidate_geo):
        signals.append(ComparisonSignal(
            code="geography_match",
            strength="medium",
            weight=20,
            value=True,
            reason="Candidate geography overlaps lead geography.",
        ))
        score += 20

    if candidate.registered_identity_match:
        signals.append(ComparisonSignal(
            code="registered_identity_match",
            strength="medium",
            weight=35,
            value=True,
            reason="Candidate has matching registered/filing identity evidence.",
        ))
        score += 35

    if candidate.corporate_social_match:
        signals.append(ComparisonSignal(
            code="corporate_social_match",
            strength="medium",
            weight=25,
            value=True,
            reason="Candidate's corporate social identity matches the supplied organization.",
        ))
        score += 25

    if candidate.parent_relationship_consistent:
        signals.append(ComparisonSignal(
            code="parent_relationship_consistent",
            strength="medium",
            weight=15,
            value=True,
            reason="Known parent/brand relationship is consistent with the candidate.",
        ))
        score += 15

    candidate_tokens = name_tokens(candidate.canonical_name)
    lead_tokens = name_tokens(_lead_name(lead))
    if lead_tokens and candidate_tokens:
        similarity = SequenceMatcher(None, " ".join(sorted(lead_tokens)), " ".join(sorted(candidate_tokens))).ratio()
        if similarity >= 0.8 and lead_name != candidate_name:
            weight = 10
            signals.append(ComparisonSignal(
                code="name_similarity",
                strength="weak",
                weight=weight,
                value=True,
                reason=f"Name similarity is {similarity:.2f}; this is candidate evidence only.",
            ))
            score += weight

    negatives = [
        ("conflicting_authoritative_domain", candidate.conflicting_authoritative_domain,
         "Candidate conflicts with an authoritative domain identity."),
        ("conflicting_geography", candidate.conflicting_geography,
         "Candidate geography conflicts with the lead in a material way."),
        ("clearly_different_legal_entity", candidate.clearly_different_legal_entity,
         "Authoritative evidence identifies a different legal entity."),
        ("historical_only", candidate.historical_only,
         "Candidate relationship is historical only while current identity is required."),
        ("external_provider_relationship", candidate.external_provider_relationship,
         "Candidate is evidenced as an external provider rather than the target organization."),
    ]
    for code, enabled, reason in negatives:
        if enabled:
            signals.append(ComparisonSignal(
                code=code,
                strength="negative",
                weight=-100,
                value=True,
                reason=reason,
            ))
            score -= 100
            hard_negative = True

    medium_count = sum(1 for signal in signals if signal.strength == "medium" and signal.value)
    strong_count = sum(1 for signal in signals if signal.code in STRONG_SIGNAL_CODES and signal.value)

    eligible = not hard_negative and (strong_count > 0 or medium_count >= 2)

    return EntityComparison(
        candidate_id=candidate.candidate_id,
        score=score,
        signals=signals,
        hard_negative=hard_negative,
        eligible_for_match=eligible,
    )
