from __future__ import annotations

import re
from datetime import UTC, datetime
from urllib.parse import urlparse

from .enrichment_contracts import (
    CompanyContact,
    CompanyFacts,
    DecisionMaker,
    EnrichmentPacket,
    Evidence,
)
from .tinyfish_client import TinyFishClient, TinyFishFetchResult, TinyFishSearchResult


_RE_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
_RE_EMPLOYEES = re.compile(r"\b(\d{1,3}(?:,\d{3})*|\d+)\s+employees\b", re.IGNORECASE)
_RE_HEADING_PERSON = re.compile(
    r"(?:^|\n)#{2,4}\s+([A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,3})\s*\n\s*"
    r"([A-Z][A-Za-z&/ ,.'’()-]{2,100})\s*(?=\n|$)",
)
_RE_DASH_PERSON = re.compile(
    r"\b([A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,3})\s*[—–-]\s*"
    r"((?:Chief|President|Founder|Co-Founder|VP|Vice President|Head|Director|SVP|EVP|CTO|CISO|CFO|COO|CEO)[^\n.;]{2,100})",
)

_ROLE_FAMILIES: tuple[tuple[str, str, int], ...] = (
    ("ciso", "security", 1),
    ("chief information security", "security", 1),
    ("security", "security", 1),
    ("fraud", "security", 1),
    ("risk", "security", 1),
    ("cto", "engineering", 2),
    ("technology", "engineering", 2),
    ("engineering", "engineering", 2),
    ("product", "product", 3),
    ("growth", "growth", 4),
    ("marketing", "growth", 4),
    ("finance", "finance", 5),
    ("procurement", "finance", 5),
    ("founder", "founder", 2),
    ("chief executive", "founder", 2),
    ("ceo", "founder", 2),
)


class TinyFishEnrichmentProvider:
    """Collect public evidence with TinyFish and build a conservative packet.

    This provider deliberately does not infer email verification, monthly
    traffic, intent scores, or unsupported company attributes. It only emits
    facts that can be traced to URLs returned by TinyFish and subsequently
    fetched in the same research run.
    """

    SEARCH_PURPOSES: tuple[tuple[str, str], ...] = (
        ("leadership", "leadership executive management team founder CEO CTO CISO"),
        ("login", "customer login sign in account authentication"),
        ("commerce", "ecommerce store checkout Shopify customer account"),
        ("security", "fraud account takeover security risk cybersecurity"),
        ("intent", "funding hiring acquisition expansion new market technology migration"),
    )

    def __init__(self, client: TinyFishClient) -> None:
        self._client = client

    def build_packet(
        self,
        *,
        company_id: int,
        domain: str,
        merchant_name: str | None = None,
        max_fetch_urls: int = 10,
    ) -> EnrichmentPacket:
        if company_id <= 0:
            raise ValueError("company_id must be positive")
        normalized_domain = domain.strip()
        if not normalized_domain:
            raise ValueError("domain must not be empty")
        if not 1 <= max_fetch_urls <= 10:
            raise ValueError("max_fetch_urls must be between 1 and 10")

        searches: list[tuple[str, list[TinyFishSearchResult]]] = []
        for purpose, suffix in self.SEARCH_PURPOSES:
            results = self._client.search(
                f"site:{normalized_domain} {suffix}", purpose=purpose
            )
            searches.append((purpose, results))

        urls = self._select_fetch_urls(searches, normalized_domain, max_fetch_urls)
        fetched = self._client.fetch(
            urls,
            purpose="evidence collection for company enrichment",
            include_links=False,
            include_page_metadata=True,
        )
        observed_at = datetime.now(UTC)
        return self._packet_from_fetched(
            company_id=company_id,
            domain=normalized_domain,
            merchant_name=merchant_name,
            fetched=fetched,
            observed_at=observed_at,
        )

    @staticmethod
    def _select_fetch_urls(
        searches: list[tuple[str, list[TinyFishSearchResult]]],
        domain: str,
        limit: int,
    ) -> list[str]:
        hostname = domain.lower().removeprefix("www.")
        selected: list[str] = []
        seen: set[str] = set()
        for _, results in searches:
            for result in results:
                parsed = urlparse(result.url)
                result_host = parsed.netloc.lower().removeprefix("www.")
                if result_host != hostname or result.url in seen:
                    continue
                seen.add(result.url)
                selected.append(result.url)
                if len(selected) == limit:
                    return selected
        return selected

    @classmethod
    def _packet_from_fetched(
        cls,
        *,
        company_id: int,
        domain: str,
        merchant_name: str | None,
        fetched: list[TinyFishFetchResult],
        observed_at: datetime,
    ) -> EnrichmentPacket:
        decision_makers = cls._extract_decision_makers(fetched, observed_at)
        company_contacts = cls._extract_company_contacts(fetched, observed_at)
        employee_values = cls._employee_values(fetched)
        evidence = cls._general_evidence(fetched, observed_at)

        notes: list[str] = [
            f"TinyFish research run fetched {len(fetched)} same-domain public URL(s).",
        ]
        if not fetched:
            notes.append("No same-domain URLs were available to fetch from TinyFish search results.")
        if len(employee_values) > 1:
            notes.append("Employee-count sources returned conflicting values; employee_count left empty.")

        facts = CompanyFacts(
            employee_count=(next(iter(employee_values)) if len(employee_values) == 1 else None),
            has_login=cls._has_login(fetched),
        )
        return EnrichmentPacket(
            company_id=company_id,
            domain=domain,
            merchant_name=merchant_name,
            company_facts=facts,
            company_contacts=company_contacts,
            decision_makers=decision_makers,
            intent_signals=[],
            personalization_angle=None,
            research_notes=notes + [
                f"Fetched evidence URLs: {', '.join(item.url for item in fetched)}"
                if fetched
                else "Fetched evidence URLs: none"
            ],
        )

    @staticmethod
    def _has_login(fetched: list[TinyFishFetchResult]) -> bool:
        login_terms = ("sign in", "log in", "login", "create an account", "customer account")
        return any(
            any(term in f"{item.title or ''}\n{item.text}".lower() for term in login_terms)
            for item in fetched
        )

    @staticmethod
    def _employee_values(fetched: list[TinyFishFetchResult]) -> set[int]:
        values: set[int] = set()
        for item in fetched:
            for match in _RE_EMPLOYEES.findall(item.text):
                values.add(int(match.replace(",", "")))
        return values

    @classmethod
    def _extract_company_contacts(
        cls, fetched: list[TinyFishFetchResult], observed_at: datetime
    ) -> list[CompanyContact]:
        contacts: dict[str, CompanyContact] = {}
        for item in fetched:
            for email in _RE_EMAIL.findall(item.text):
                normalized = email.casefold()
                contacts.setdefault(
                    normalized,
                    CompanyContact(
                        channel="email",
                        value=email,
                        normalized_value=normalized,
                        label="public_email",
                        source="tinyfish_fetch",
                        source_url=item.url,
                        confidence=1.0,
                        evidence=[
                            Evidence(
                                claim_type="public_company_email",
                                claim={"email": email},
                                source_url=item.url,
                                source_type="tinyfish_fetch",
                                observed_at=observed_at,
                                confidence=1.0,
                            )
                        ],
                    ),
                )
        return list(contacts.values())

    @classmethod
    def _extract_decision_makers(
        cls, fetched: list[TinyFishFetchResult], observed_at: datetime
    ) -> list[DecisionMaker]:
        found: dict[tuple[str, str], DecisionMaker] = {}
        for item in fetched:
            pairs = list(_RE_HEADING_PERSON.findall(item.text)) + list(
                _RE_DASH_PERSON.findall(item.text)
            )
            for name, title in pairs:
                clean_name = " ".join(name.split())
                clean_title = " ".join(title.split()).strip("-—– ")
                family, priority = cls._role_family(clean_title)
                if family is None:
                    continue
                key = (clean_name.casefold(), clean_title.casefold())
                found.setdefault(
                    key,
                    DecisionMaker(
                        full_name=clean_name,
                        title=clean_title,
                        role_family=family,
                        role_priority=priority,
                        rationale="Public leadership evidence collected from the fetched company page.",
                        confidence=1.0,
                        evidence=[
                            Evidence(
                                claim_type="public_decision_maker",
                                claim={"name": clean_name, "title": clean_title},
                                source_url=item.url,
                                source_type="tinyfish_fetch",
                                observed_at=observed_at,
                                confidence=1.0,
                            )
                        ],
                    ),
                )
        return sorted(found.values(), key=lambda item: (item.role_priority or 99, item.full_name))

    @staticmethod
    def _role_family(title: str) -> tuple[str | None, int | None]:
        lowered = title.casefold()
        for needle, family, priority in _ROLE_FAMILIES:
            if needle in lowered:
                return family, priority
        return None, None

    @staticmethod
    def _general_evidence(
        fetched: list[TinyFishFetchResult], observed_at: datetime
    ) -> list[Evidence]:
        evidence: list[Evidence] = []
        for item in fetched:
            lower_text = item.text.lower()
            if any(term in lower_text for term in ("sign in", "log in", "login", "customer account")):
                evidence.append(
                    Evidence(
                        claim_type="customer_login_surface",
                        claim={"url": item.final_url or item.url},
                        source_url=item.url,
                        source_type="tinyfish_fetch",
                        observed_at=observed_at,
                        confidence=1.0,
                    )
                )
        return evidence
