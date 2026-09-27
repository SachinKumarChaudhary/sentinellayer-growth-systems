from __future__ import annotations

from sentinellayer_growth_engine.phase1.models import Phase1Handoff

from .models import EntityCandidate
from .normalization import geography_tokens, name_tokens, normalize_domain, registrable_domain


DEFAULT_CANDIDATE_BUDGET = 25


def _lead_name(lead: Phase1Handoff) -> str:
    return lead.canonical_lead.legal_name or lead.canonical_lead.display_name or ""


def _candidate_alias_tokens(candidate: EntityCandidate) -> frozenset[str]:
    tokens: set[str] = set()
    for alias in [candidate.canonical_name, *candidate.aliases]:
        tokens.update(name_tokens(alias))
    return frozenset(tokens)


def _is_block_match(lead: Phase1Handoff, candidate: EntityCandidate) -> bool:
    lead_domain = normalize_domain(lead.canonical_lead.domain)
    candidate_domain = normalize_domain(candidate.canonical_domain)
    if lead_domain and candidate_domain:
        if lead_domain == candidate_domain:
            return True
        if registrable_domain(lead_domain) == registrable_domain(candidate_domain):
            return True

    lead_tokens = name_tokens(_lead_name(lead))
    alias_tokens = _candidate_alias_tokens(candidate)
    if lead_tokens and alias_tokens and lead_tokens.intersection(alias_tokens):
        return True

    lead_geo = geography_tokens(
        [lead.canonical_lead.country_code or "", lead.canonical_lead.region or "", lead.canonical_lead.city or ""]
    )
    candidate_geo = geography_tokens(candidate.geography)
    if lead_geo and candidate_geo and lead_geo.intersection(candidate_geo) and lead_tokens.intersection(alias_tokens):
        return True

    return False


def generate_candidates(
    lead: Phase1Handoff,
    candidates: list[EntityCandidate],
    *,
    budget: int = DEFAULT_CANDIDATE_BUDGET,
) -> list[EntityCandidate]:
    if budget <= 0:
        raise ValueError("candidate budget must be positive")

    selected = [candidate for candidate in candidates if _is_block_match(lead, candidate)]

    # Preserve deterministic input ordering while enforcing the hard budget.
    return selected[:budget]
