from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


_LINKEDIN_HOSTS = {"linkedin.com", "www.linkedin.com"}
_LINKEDIN_PROFILE_RE = re.compile(r"^/in/[^/]+/?$")


@dataclass(frozen=True)
class DecisionMakerCandidate:
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
    if host not in _LINKEDIN_HOSTS or not _LINKEDIN_PROFILE_RE.match(parsed.path):
        return None
    slug = parsed.path.rstrip("/").split("/")[-1]
    safe_query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=False) if k == "locale"]
    return urlunparse(("https", "www.linkedin.com", f"/in/{slug}", "", urlencode(safe_query), ""))


def merge_candidate_sources(*candidates: DecisionMakerCandidate) -> DecisionMakerCandidate:
    if not candidates:
        raise ValueError("at least one candidate is required")
    base = max(candidates, key=lambda c: c.overall_confidence)
    return DecisionMakerCandidate(
        full_name=base.full_name,
        title=base.title,
        company_name=base.company_name,
        company_domain=base.company_domain,
        linkedin_url=next((normalize_linkedin_url(c.linkedin_url or "") for c in candidates if c.linkedin_url), None),
        source_urls=tuple(dict.fromkeys(url for c in candidates for url in c.source_urls if url)),
        source_types=tuple(dict.fromkeys(t for c in candidates for t in c.source_types if t)),
        current_employer_confidence=max(c.current_employer_confidence for c in candidates),
        title_confidence=max(c.title_confidence for c in candidates),
        identity_confidence=max(c.identity_confidence for c in candidates),
        linkedin_confidence=max(c.linkedin_confidence for c in candidates),
        overall_confidence=max(c.overall_confidence for c in candidates),
        status=base.status,
        reasons=tuple(dict.fromkeys(r for c in candidates for r in c.reasons if r)),
    )


def score_identity(*, name_matches: bool, current_company_matches: bool, title_matches: bool,
                   company_site_supports_person: bool, independent_source_supports_person: bool,
                   former_employee: bool = False, ambiguous_name: bool = False,
                   stale_employment: bool = False) -> tuple[float, tuple[str, ...]]:
    score = 0.0
    reasons: list[str] = []
    if name_matches:
        score += 0.30; reasons.append("name_match")
    if current_company_matches:
        score += 0.30; reasons.append("current_company_match")
    if title_matches:
        score += 0.20; reasons.append("title_match")
    if company_site_supports_person:
        score += 0.10; reasons.append("company_site_support")
    if independent_source_supports_person:
        score += 0.10; reasons.append("independent_source_support")
    if former_employee:
        score -= 0.25; reasons.append("former_employee_penalty")
    if stale_employment:
        reasons.append("stale_employment_penalty")
        if not former_employee:
            score -= 0.15
    if ambiguous_name:
        score -= 0.20; reasons.append("ambiguous_name_penalty")
    return max(0.0, min(1.0, score)), tuple(reasons)


def outreach_status(confidence: float, *, linkedin_url: str | None,
                    current_company_confidence: float, title_confidence: float = 1.0) -> str:
    if not linkedin_url or current_company_confidence < 0.75 or title_confidence < 0.75:
        return "review"
    if confidence >= 0.90:
        return "outreach_ready"
    if confidence >= 0.75:
        return "strong_candidate"
    return "review"


def rank_candidates(candidates: list[DecisionMakerCandidate]) -> list[DecisionMakerCandidate]:
    return sorted(candidates, key=lambda c: (
        c.status == "outreach_ready", c.overall_confidence,
        c.linkedin_confidence, c.current_employer_confidence,
    ), reverse=True)
