from __future__ import annotations

import re
from urllib.parse import urlparse

from .decision_maker_resolution import normalize_linkedin_url, outreach_status, rank_candidates, score_identity, DecisionMakerCandidate
from .enrichment_contracts import ContactMethod, DecisionMaker, EnrichmentPacket, Evidence


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
    slug_tokens = tuple(re.findall(r"[a-z0-9]+", urlparse(linkedin_url).path.rstrip("/").split("/")[-1].casefold()))
    name_tokens = _normalize_name(full_name)
    return len(name_tokens) >= 2 and len(slug_tokens) >= 2 and all(token in slug_tokens for token in name_tokens)


def _person_evidence(item: Evidence, full_name: str) -> bool:
    claim = item.claim or {}
    name = str(claim.get("name") or claim.get("full_name") or "").strip()
    return bool(name) and _normalize_name(name) == _normalize_name(full_name)


def _employment_flags(evidence: list[Evidence]) -> tuple[bool, bool]:
    former = False
    stale = False
    for item in evidence:
        claim = item.claim or {}
        claim_type = (item.claim_type or "").casefold()
        text = " ".join(str(value).casefold() for value in claim.values())
        former |= any(token in claim_type or token in text for token in ("former", "ex-", "previous employer", "past employer"))
        stale |= any(key in claim for key in ("end_date", "ended_at", "employment_end"))
        stale |= claim.get("current") is False or claim.get("is_current") is False
    return former, stale


def _title_conflict(evidence: list[Evidence], title: str | None) -> bool:
    operating = (title or "").casefold()
    if not any(token in operating for token in ("cto", "chief technology", "vp engineering", "head of engineering", "ciso", "chief information security", "head of security", "coo", "chief operating", "cfo", "chief financial", "vp finance", "head of finance")):
        return False
    for item in evidence:
        text = " ".join(str(value).casefold() for value in (item.claim or {}).values())
        if "non-executive board director" in text or "non executive board director" in text:
            return True
        if re.search(r"\b(?:former|ex|previously)\s+(?:cto|ciso|coo|cfo|chief technology officer|chief information security officer|chief operating officer|chief financial officer)\b", text):
            return True
    return False


def _candidate(dm: DecisionMaker, packet: EnrichmentPacket) -> DecisionMakerCandidate:
    linkedin = next((normalize_linkedin_url(c.normalized_value or c.value) for c in dm.contacts if c.channel == "linkedin"), None)
    person = [e for e in dm.evidence if _person_evidence(e, dm.full_name)]
    hosts = {_host(e.source_url) for e in person if e.source_url and _host(e.source_url) != "linkedin.com"}
    company_site = any(_domain_matches(e.source_url, packet.domain) for e in person)
    independent = len(hosts) >= 2
    slug_match = _linkedin_slug_matches_name(linkedin, dm.full_name)
    former, stale = _employment_flags(person)
    title_stale = _title_conflict(person, dm.title)
    current_company = company_site or any(
        "company" in (e.claim_type or "").casefold()
        and (str(e.claim.get("company_domain", "")).casefold().removeprefix("www.") == packet.domain.casefold().removeprefix("www.")
             or (packet.merchant_name and str(e.claim.get("company_name", "")).casefold() == packet.merchant_name.casefold()))
        for e in person
    )
    if former or stale:
        current_company = False
    identity, reasons = score_identity(
        name_matches=slug_match or independent,
        current_company_matches=current_company,
        title_matches=bool(dm.title or dm.role_family),
        company_site_supports_person=company_site,
        independent_source_supports_person=independent,
        former_employee=former,
        stale_employment=stale,
        ambiguous_name=bool(linkedin and not slug_match),
    )
    if title_stale:
        reasons = (*reasons, "current_title_conflict")
    employer = 0.0 if former or stale else (0.95 if company_site and independent else 0.85 if company_site else 0.75 if current_company else 0.0)
    linkedin_conf = 0.95 if linkedin and slug_match else 0.80 if linkedin else 0.0
    title_conf = 0.0 if title_stale else 1.0 if (dm.title or dm.role_family) else 0.0
    overall = min(1.0, identity * 0.65 + employer * 0.20 + linkedin_conf * 0.15)
    return DecisionMakerCandidate(
        full_name=dm.full_name, title=dm.title, company_name=packet.merchant_name,
        company_domain=packet.domain, linkedin_url=linkedin,
        source_urls=tuple(dict.fromkeys([e.source_url for e in dm.evidence if e.source_url] + [c.source_url for c in dm.contacts if c.source_url])),
        source_types=tuple(dict.fromkeys(e.source_type for e in dm.evidence if e.source_type)),
        current_employer_confidence=employer, title_confidence=title_conf,
        identity_confidence=identity, linkedin_confidence=linkedin_conf,
        overall_confidence=overall,
        status=outreach_status(overall, linkedin_url=linkedin, current_company_confidence=employer, title_confidence=title_conf),
        reasons=reasons,
    )


def resolve_decision_makers(packet: EnrichmentPacket) -> EnrichmentPacket:
    resolved = packet.model_copy(deep=True)
    candidates = [_candidate(dm, resolved) for dm in resolved.decision_makers]
    ranked = rank_candidates(candidates)
    by_key = {(c.full_name.casefold(), (c.title or "").casefold()): c for c in ranked}
    output: list[DecisionMaker] = []
    for dm in resolved.decision_makers:
        c = by_key[(dm.full_name.casefold(), (dm.title or "").casefold())]
        contacts = list(dm.contacts)
        if c.linkedin_url:
            existing = next((x for x in contacts if x.channel == "linkedin"), None)
            if existing:
                existing.value = c.linkedin_url; existing.normalized_value = c.linkedin_url
                existing.verification_status = "candidate"; existing.confidence = c.linkedin_confidence
            else:
                contacts.append(ContactMethod(channel="linkedin", value=c.linkedin_url, normalized_value=c.linkedin_url, source="deterministic_resolution", source_url=c.linkedin_url, verification_status="candidate", confidence=c.linkedin_confidence))
        evidence = list(dm.evidence)
        if c.source_urls:
            evidence.append(Evidence(
                claim_type="decision_maker_identity_resolution",
                claim={"identity_confidence": round(c.identity_confidence, 4), "current_employer_confidence": round(c.current_employer_confidence, 4), "linkedin_confidence": round(c.linkedin_confidence, 4), "outreach_status": c.status, "reasons": list(c.reasons)},
                source_url=c.source_urls[0], source_type="deterministic_resolution", confidence=c.overall_confidence,
            ))
        output.append(dm.model_copy(update={"confidence": c.overall_confidence, "contacts": contacts, "evidence": evidence}))
    resolved.decision_makers = sorted(output, key=lambda dm: by_key[(dm.full_name.casefold(), (dm.title or "").casefold())].overall_confidence, reverse=True)
    return resolved


class ResolvedTinyFishProvider:
    def __init__(self, provider: object) -> None:
        self._provider = provider

    def build_packet(self, **kwargs: object) -> EnrichmentPacket:
        packet = self._provider.build_packet(**kwargs)  # type: ignore[attr-defined]
        if not isinstance(packet, EnrichmentPacket):
            raise TypeError("TinyFish provider returned an invalid enrichment packet")
        return resolve_decision_makers(packet)
