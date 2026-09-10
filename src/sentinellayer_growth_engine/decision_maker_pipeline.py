from __future__ import annotations

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


def _title_matches(dm: DecisionMaker) -> bool:
    return bool(dm.title or dm.role_family)


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
    source_types = tuple(dict.fromkeys(e.source_type for e in dm.evidence if e.source_type))
    non_linkedin_hosts = {
        _host(url) for url in source_urls if url and _host(url) not in {"linkedin.com"}
    }
    company_site_support = any(_domain_matches(url, packet.domain) for url in source_urls)
    independent_support = len(non_linkedin_hosts) >= 2
    name_matches = bool(dm.full_name.strip())
    current_company_matches = company_site_support or any(
        "company" in (e.claim_type or "").lower() and bool(e.claim) for e in dm.evidence
    )
    title_matches = _title_matches(dm)
    identity, reasons = score_identity(
        name_matches=name_matches,
        current_company_matches=current_company_matches,
        title_matches=title_matches,
        company_site_supports_person=company_site_support,
        independent_source_supports_person=independent_support,
    )
    employer_confidence = 0.85 if company_site_support else (0.75 if current_company_matches else 0.0)
    linkedin_confidence = 0.95 if linkedin_url else 0.0
    overall = min(1.0, identity * 0.65 + employer_confidence * 0.20 + linkedin_confidence * 0.15)
    status = outreach_status(
        overall,
        linkedin_url=linkedin_url,
        current_company_confidence=employer_confidence,
    )
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
    by_name = {c.full_name.casefold(): c for c in ranked}
    output: list[DecisionMaker] = []

    for dm in resolved.decision_makers:
        candidate = by_name[dm.full_name.casefold()]
        contacts = list(dm.contacts)
        if candidate.linkedin_url:
            for contact in contacts:
                if contact.channel == "linkedin":
                    contact.normalized_value = candidate.linkedin_url
                    contact.value = candidate.linkedin_url
                    contact.confidence = candidate.linkedin_confidence
                    contact.verification_status = "candidate"
                    break
        evidence = list(dm.evidence)
        if candidate.source_urls:
            evidence.append(
                Evidence(
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
                )
            )
        output.append(
            dm.model_copy(
                update={
                    "confidence": candidate.overall_confidence,
                    "contacts": contacts,
                    "evidence": evidence,
                }
            )
        )

    resolved.decision_makers = sorted(
        output,
        key=lambda item: by_name[item.full_name.casefold()].overall_confidence,
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
