from __future__ import annotations

import re
from urllib.parse import urlparse

from .decision_maker_resolution import (
    DecisionMakerCandidate,
    normalize_linkedin_url,
    outreach_status,
    rank_candidates,
    score_identity,
)
from .enrichment_contracts import DecisionMaker, EnrichmentPacket, Evidence


def _host(value: str | None) -> str:
    if not value:
        return ""
    return urlparse(value).netloc.lower().removeprefix("www.").split(":", 1)[0]


def _domain_matches(url: str | None, domain: str) -> bool:
    host = _host(url)
    target = domain.lower().strip().removeprefix("www.").split(":", 1)[0]
    return bool(host and target and (host == target or host.endswith("." + target)))


def _normalize_name(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9]+", value.casefold()))


def _linkedin_slug_matches_name(linkedin_url: str | None, full_name: str) -> bool:
    if not linkedin_url:
        return False
    slug = urlparse(linkedin_url).path.rstrip("/").split("/")[-1].casefold()
    slug_tokens = tuple(re.findall(r"[a-z0-9]+", slug))
    name_tokens = _normalize_name(full_name)
    if len(name_tokens) < 2 or len(slug_tokens) < 2:
        return False
    return all(token in slug_tokens for token in name_tokens) or slug_tokens == name_tokens


def _title_matches(dm: DecisionMaker) -> bool:
    return bool(dm.title and dm.title.strip()) or bool(dm.role_family and dm.role_family.strip())


def _person_evidence(evidence: Evidence, full_name: str) -> bool:
    """Require the source claim to attest to this person, not merely the company."""
    claim = evidence.claim or {}
    name = str(claim.get("name") or claim.get("full_name") or "").strip()
    if not name:
        return False
    return _normalize_name(name) == _normalize_name(full_name)


def _employment_flags(evidence: list[Evidence]) -> tuple[bool, bool]:
    """Detect explicit former/stale employment markers without guessing from age alone."""
    former = False
    stale = False
    for item in evidence:
        claim = item.claim or {}
        claim_type = (item.claim_type or "").casefold()
        text = " ".join(str(value).casefold() for value in claim.values())
        if any(token in claim_type or token in text for token in ("former", "ex-", "previous employer", "past employer")):
            former = True
        if any(key in claim for key in ("end_date", "ended_at", "employment_end")):
            stale = True
        if claim.get("current") is False or claim.get("is_current") is False:
            stale = True
    return former, stale


def _linkedin_contact(dm: DecisionMaker) -> tuple[str | None, object | None]:
    for contact in dm.contacts:
        if contact.channel != "linkedin":
            continue
        normalized = normalize_linkedin_url(contact.normalized_value or contact.value)
        if normalized:
            return normalized, contact
    return None, None


def _candidate_from_decision_maker(dm: DecisionMaker, packet: EnrichmentPacket) -> DecisionMakerCandidate:
    linkedin_url, linkedin_contact = _linkedin_contact(dm)
    source_urls = tuple(
        dict.fromkeys(
            [e.source_url for e in dm.evidence if e.source_url]
            + [getattr(linkedin_contact, "source_url", None)]
        )
    )
    source_urls = tuple(url for url in source_urls if url)
    source_types = tuple(dict.fromkeys(e.source_type for e in dm.evidence if e.source_type))
    person_evidence = [e for e in dm.evidence if _person_evidence(e, dm.full_name)]
    non_linkedin_hosts = {
        _host(url)
        for url in [e.source_url for e in person_evidence if e.source_url]
        if url and _host(url) not in {"linkedin.com"}
    }
    company_site_support = any(_domain_matches(e.source_url, packet.domain) for e in person_evidence)
    independent_support = len(non_linkedin_hosts) >= 2
    name_observation_count = len(non_linkedin_hosts)
    linkedin_name_match = _linkedin_slug_matches_name(linkedin_url, dm.full_name)
    name_matches = linkedin_name_match or name_observation_count >= 2
    current_company_matches = company_site_support or any(
        ("company" in (e.claim_type or "").casefold())
        and bool(e.claim.get("company_name") or e.claim.get("company_domain"))
        and (
            str(e.claim.get("company_domain", "")).casefold().removeprefix("www.")
            == packet.domain.casefold().removeprefix("www.")
            or (
                packet.merchant_name
                and str(e.claim.get("company_name", "")).casefold() == packet.merchant_name.casefold()
            )
        )
        for e in person_evidence
    )
    former_employee, stale_employment = _employment_flags(person_evidence)
    if former_employee or stale_employment:
        current_company_matches = False
    title_matches = _title_matches(dm)
    identity, reasons = score_identity(
        name_matches=name_matches,
        current_company_matches=current_company_matches,
        title_matches=title_matches,
        company_site_supports_person=company_site_support,
        independent_source_supports_person=independent_support,
        former_employee=former_employee,
        stale_employment=stale_employment,
        ambiguous_name=bool(linkedin_url and not linkedin_name_match),
    )
    if former_employee or stale_employment:
        employer_confidence = 0.0
    elif company_site_support and independent_support:
        employer_confidence = 0.95
    elif company_site_support:
        employer_confidence = 0.85
    elif current_company_matches:
        employer_confidence = 0.75
    else:
        employer_confidence = 0.0
    linkedin_confidence = 0.95 if linkedin_url and linkedin_name_match else (0.80 if linkedin_url else 0.0)
    overall = min(1.0, identity * 0.65 + employer_confidence * 0.20 + linkedin_confidence * 0.15)
    status = outreach_status(overall, linkedin_url=linkedin_url, current_company_confidence=employer_confidence)
    return DecisionMakerCandidate(
        full_name=dm.full_name,
        title=dm.title,
        company_name=packet.merchant_name,
        company_domain=packet.domain,
        linkedin_url=linkedin_url,
        source_urls=source_urls,
        source_types=source_types,
        current_employer_confidence=employer_confidence,
        title_confidence=1.0 if title_matches else 0.0,
        identity_confidence=identity,
        linkedin_confidence=linkedin_confidence,
        overall_confidence=overall,
        status=status,
        reasons=reasons,
    )


def resolve_decision_makers(packet: EnrichmentPacket) -> EnrichmentPacket:
    """Resolve discovered decision makers before persistence; never invent evidence."""
    resolved = packet.model_copy(deep=True)
    candidates = [_candidate_from_decision_maker(dm, resolved) for dm in resolved.decision_makers]
    ranked = rank_candidates(candidates)
    by_key = {(c.full_name.casefold(), (c.title or "").casefold()): c for c in ranked}
    output: list[DecisionMaker] = []

    for dm in resolved.decision_makers:
        candidate = by_key[(dm.full_name.casefold(), (dm.title or "").casefold())]
        contacts = list(dm.contacts)
        if candidate.linkedin_url:
            linkedin_found = False
            for contact in contacts:
                if contact.channel == "linkedin":
                    contact.normalized_value = candidate.linkedin_url
                    contact.value = candidate.linkedin_url
                    contact.confidence = candidate.linkedin_confidence
                    contact.verification_status = "candidate"
                    linkedin_found = True
                    break
            if not linkedin_found:
                from .enrichment_contracts import ContactMethod
                contacts.append(ContactMethod(
                    channel="linkedin",
                    value=candidate.linkedin_url,
                    normalized_value=candidate.linkedin_url,
                    source="deterministic_resolution",
                    source_url=candidate.linkedin_url,
                    verification_status="candidate",
                    confidence=candidate.linkedin_confidence,
                ))
        evidence = list(dm.evidence)
        if candidate.source_urls:
            evidence.append(Evidence(
                claim_type="decision_maker_identity_resolution",
                claim={
                    "identity_confidence": round(candidate.identity_confidence, 4),
                    "current_employer_confidence": round(candidate.current_employer_confidence, 4),
                    "linkedin_confidence": round(candidate.linkedin_confidence, 4),
                    "outreach_status": candidate.status,
                    "reasons": list(candidate.reasons),
                },
                source_url=candidate.source_urls[0],
                source_type="deterministic_resolution",
                confidence=candidate.overall_confidence,
            ))
        output.append(dm.model_copy(update={
            "confidence": candidate.overall_confidence,
            "contacts": contacts,
            "evidence": evidence,
        }))

    resolved.decision_makers = sorted(
        output,
        key=lambda item: by_key[(item.full_name.casefold(), (item.title or "").casefold())].overall_confidence,
        reverse=True,
    )
    return resolved


class ResolvedTinyFishProvider:
    """Adapter that makes deterministic DM resolution part of TinyFish enrichment."""

    def __init__(self, provider: object) -> None:
        self._provider = provider

    def build_packet(self, **kwargs: object) -> EnrichmentPacket:
        packet = self._provider.build_packet(**kwargs)  # type: ignore[attr-defined]
        if not isinstance(packet, EnrichmentPacket):
            raise TypeError("TinyFish provider returned an invalid enrichment packet")
        return resolve_decision_makers(packet)
