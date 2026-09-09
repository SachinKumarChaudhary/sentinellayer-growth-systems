from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse


_ROLE_MARKER_RE = re.compile(
    r"\b(?:chief\s+(?:executive|technology|information security|financial|operating|product|marketing|revenue|risk)|"
    r"ceo|cto|ciso|cfo|coo|cio|president|vice president|vp|svp|evp|head of|director of|director|founder|co-founder)\b",
    re.IGNORECASE,
)
_NAME_RE = re.compile(
    r"^[A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,3}$"
)
_STOPWORDS = {
    "the", "and", "company", "co", "corp", "corporation", "inc", "llc", "ltd",
    "limited", "group", "holdings", "international", "global",
}
_GENERIC_EMAIL_PREFIXES = {
    "info", "hello", "support", "sales", "contact", "careers", "hr", "team", "press",
}


@dataclass(frozen=True)
class DecisionMakerQuality:
    valid: bool
    reason: str


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if token not in _STOPWORDS and len(token) > 1
    }


def is_valid_decision_maker(company_name: str, full_name: str, title: str | None) -> DecisionMakerQuality:
    name = " ".join(full_name.split()).strip()
    normalized_title = " ".join((title or "").split()).strip()
    if not _NAME_RE.fullmatch(name):
        return DecisionMakerQuality(False, "invalid_person_name_format")
    if not normalized_title or not _ROLE_MARKER_RE.search(normalized_title):
        return DecisionMakerQuality(False, "title_lacks_explicit_executive_role")

    person_tokens = _tokens(name)
    company_tokens = _tokens(company_name)
    if person_tokens and company_tokens and (
        person_tokens <= company_tokens or company_tokens <= person_tokens
    ):
        return DecisionMakerQuality(False, "name_overlaps_company_identity")
    return DecisionMakerQuality(True, "accepted")


def is_valid_company_email(company_domain: str, email: str, source_url: str | None = None) -> bool:
    value = email.strip().casefold()
    if "@" not in value:
        return False
    local, email_domain = value.rsplit("@", 1)
    if not local or not email_domain:
        return False
    if local in _GENERIC_EMAIL_PREFIXES:
        return True

    normalized_company_domain = company_domain.casefold().removeprefix("www.").strip()
    if email_domain == normalized_company_domain or email_domain.endswith("." + normalized_company_domain):
        return True

    if source_url:
        host = urlparse(source_url).netloc.casefold().removeprefix("www.")
        if host == normalized_company_domain or host.endswith("." + normalized_company_domain):
            return True
    return False
