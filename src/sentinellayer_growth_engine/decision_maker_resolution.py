from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


_LINKEDIN_HOSTS = {"linkedin.com", "www.linkedin.com"}
_LINKEDIN_PROFILE_RE = re.compile(r"^/in/[^/]+/?$")


@dataclass(frozen=True)
class DecisionMakerCandidate:
    """A discovered person before promotion to a canonical DecisionMaker."""

    full_name: str
    title: str | None = None
    company_name: str | None = None
    company_domain: str | None = None
    linkedin_url: str | None = None
    source_urls: tuple[str, ...] = ()
    source_types: tuple[str, ...] = ()
    current_employer_confidence: float = 0.0
    title_confidence: float = 0.0
    identity_confidence: float = 0.0
    linkedin_confidence: float = 0.0
    overall_confidence: float = 0.0
    status: str = "candidate"
    reasons: tuple[str, ...] = ()


def normalize_linkedin_url(value: str) -> str | None:
    """Return a canonical public LinkedIn profile URL, or None for non-profile URLs."""
    raw = value.strip()
    if not raw:
        return None
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    parsed = urlparse(raw)
    host = parsed.netloc.lower().removeprefix("www.")
    if host != "linkedin.com" or not _LINKEDIN_PROFILE_RE.match(parsed.path):
        return None
    slug = parsed.path.rstrip("/").split("/")[-1]
    # Keep only benign profile query parameters; tracking parameters are discarded.
    safe_query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=False) if k in {"locale"}]
    query = urlencode(safe_query)
    return urlunparse(("https", "www.linkedin.com", f"/in/{slug}", "", query, ""))


def merge_candidate_sources(*candidates: DecisionMakerCandidate) -> DecisionMakerCandidate:
    """Merge observations of the same person while preserving all source provenance."""
    if not candidates:
        raise ValueError("at least one candidate is required")
    base = max(candidates, key=lambda c: c.overall_confidence)
    source_urls = tuple(dict.fromkeys(url for c in candidates for url in c.source_urls if url))
    source_types = tuple(dict.fromkeys(t for c in candidates for t in c.source_types if t))
    reasons = tuple(dict.fromkeys(r for c in candidates for r in c.reasons if r))
    linkedin = next((normalize_linkedin_url(c.linkedin_url or "") for c in candidates if c.linkedin_url), None)
    return DecisionMakerCandidate(
        full_name=base.full_name,
        title=base.title,
        company_name=base.company_name,
        company_domain=base.company_domain,
        linkedin_url=linkedin,
        source_urls=source_urls,
        source_types=source_types,
        current_employer_confidence=max(c.current_employer_confidence for c in candidates),
        title_confidence=max(c.title_confidence for c in candidates),
        identity_confidence=max(c.identity_confidence for c in candidates),
        linkedin_confidence=max(c.linkedin_confidence for c in candidates),
        overall_confidence=max(c.overall_confidence for c in candidates),
        status=base.status,
        reasons=reasons,
    )


def score_identity(
    *,
    name_matches: bool,
    current_company_matches: bool,
    title_matches: bool,
    company_site_supports_person: bool,
    independent_source_supports_person: bool,
    former_employee: bool = False,
    ambiguous_name: bool = False,
    stale_employment: bool = False,
) -> tuple[float, tuple[str, ...]]:
    """Score person/company identity conservatively; weights are intentionally transparent."""
    score = 0.0
    reasons: list[str] = []
    if name_matches:
        score += 0.30
        reasons.append("name_match")
    if current_company_matches:
        score += 0.30
        reasons.append("current_company_match")
    if title_matches:
        score += 0.20
        reasons.append("title_match")
    if company_site_supports_person:
        score += 0.10
        reasons.append("company_site_support")
    if independent_source_supports_person:
        score += 0.10
        reasons.append("independent_source_support")
    if former_employee:
        score -= 0.30
        reasons.append("former_employee_penalty")
    if ambiguous_name:
        score -= 0.20
        reasons.append("ambiguous_name_penalty")
    if stale_employment:
        score -= 0.15
        reasons.append("stale_employment_penalty")
    return max(0.0, min(1.0, score)), tuple(reasons)


def outreach_status(confidence: float, *, linkedin_url: str | None, current_company_confidence: float) -> str:
    """Determine the operational state before a person is eligible for outreach."""
    if not linkedin_url:
        return "review"
    if current_company_confidence < 0.75:
        return "review"
    if confidence >= 0.90:
        return "outreach_ready"
    if confidence >= 0.75:
        return "strong_candidate"
    return "review"


def rank_candidates(candidates: list[DecisionMakerCandidate]) -> list[DecisionMakerCandidate]:
    """Return strongest candidates first without mutating canonical data."""
    return sorted(
        candidates,
        key=lambda c: (
            c.status == "outreach_ready",
            c.overall_confidence,
            c.linkedin_confidence,
            c.current_employer_confidence,
        ),
        reverse=True,
    )
