from __future__ import annotations

import re
from datetime import UTC, date, datetime
from urllib.parse import urlparse

from .enrichment_contracts import (
    CompanyContact,
    CompanyFacts,
    DecisionMaker,
    EnrichmentPacket,
    Evidence,
    IntentSignal,
)
from .intent_normalization import normalize_signal
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
_RE_ISO_DATE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_RE_LONG_DATE = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{1,2}(?:st|nd|rd|th)?(?:,|\s)\s*20\d{2}\b",
    re.IGNORECASE,
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

_INTENT_PATTERNS: tuple[tuple[str, tuple[re.Pattern[str], ...], float], ...] = (
    (
        "funding",
        (
            re.compile(r"\b(?:raised|raises|raising|secured|closed)\s+(?:a\s+)?(?:\$|€|£)?[\d,.]+\s*(?:million|billion|m|bn)?\s*(?:in\s+)?(?:funding|financing|investment)", re.I),
            re.compile(r"\b(?:series\s+[a-f]|seed|venture)\s+(?:funding|round|financing)\b", re.I),
        ),
        0.90,
    ),
    (
        "new_c_suite",
        (
            re.compile(r"\b(?:appointed|named|joins?|joined|promoted)\b[^.\n]{0,100}\b(?:CEO|CFO|CTO|CPO|CMO|CISO|COO)\b", re.I),
            re.compile(r"\b(?:new|incoming)\s+(?:CEO|CFO|CTO|CPO|CMO|CISO|COO)\b", re.I),
        ),
        0.90,
    ),
    (
        "security_hiring",
        (
            re.compile(r"\b(?:hiring|hire|recruiting|recruit)\b[^.\n]{0,120}\b(?:security|fraud|trust\s*(?:and|&)\s*safety|risk|identity)\b", re.I),
            re.compile(r"\b(?:security|fraud|trust\s*(?:and|&)\s*safety|risk|identity)\b[^.\n]{0,120}\b(?:hiring|hire|recruiting|recruit)\b", re.I),
        ),
        0.85,
    ),
    (
        "tech_migration",
        (
            re.compile(r"\b(?:migrat(?:e|ed|ing)|replatform(?:ed|ing)?|move|moved|moving)\b[^.\n]{0,120}\b(?:platform|technology|stack|Shopify|Next\.js|cloud)\b", re.I),
            re.compile(r"\b(?:platform|technology|stack)\b[^.\n]{0,120}\b(?:migration|migrated|replatformed)\b", re.I),
        ),
        0.85,
    ),
    (
        "new_market",
        (
            re.compile(r"\b(?:launch(?:ed|ing)?|enter(?:ed|ing)?|expand(?:ed|ing)?)\b[^.\n]{0,120}\b(?:market|country|Europe|EU|UK|APAC|Asia|Canada|Australia)\b", re.I),
            re.compile(r"\b(?:expanded|expanding)\s+to\s+(?:the\s+)?(?:UK|Europe|EU|Canada|Australia|Asia|APAC)\b", re.I),
        ),
        0.80,
    ),
    (
        "franchise_launch",
        (
            re.compile(r"\b(?:launch(?:ed|ing)?|open(?:ed|ing)?)\b[^.\n]{0,100}\b(?:franchise|franchises|franchisee|location|store)\b", re.I),
        ),
        0.80,
    ),
    (
        "regulated_expansion",
        (
            re.compile(r"\b(?:expand(?:ed|ing)?|launch(?:ed|ing)?|enter(?:ed|ing)?)\b[^.\n]{0,120}\b(?:regulated|regulated category|compliance regime)\b", re.I),
        ),
        0.80,
    ),
    (
        "pci",
        (re.compile(r"\bPCI(?:\s+DSS)?(?:\s+4\.0)?\b", re.I),),
        0.90,
    ),
    (
        "gdpr",
        (re.compile(r"\bGDPR\b", re.I),),
        0.85,
    ),
    (
        "dpdp",
        (re.compile(r"\b(?:DPDP|Digital Personal Data Protection)\b", re.I),),
        0.85,
    ),
    (
        "soc2_requirement",
        (re.compile(r"\b(?:SOC\s*2|SOC2)\b[^.\n]{0,100}\b(?:requirement|required|procurement|vendor security review)\b", re.I),),
        0.85,
    ),
    (
        "ca_breach",
        (re.compile(r"\b(?:California breach|California data breach|SB\s*362)\b", re.I),),
        0.90,
    ),
    (
        "ftc_click_to_cancel",
        (re.compile(r"\b(?:FTC|click[- ]to[- ]cancel)\b[^.\n]{0,100}\b(?:subscription|rule|requirement|cancel)\b", re.I),),
        0.85,
    ),
    (
        "award",
        (re.compile(r"\b(?:named|won|received|recognized)\b[^.\n]{0,100}\b(?:award|awards|recognition)\b", re.I),),
        0.75,
    ),
)


class TinyFishEnrichmentProvider:
    """Collect public evidence with TinyFish and build a conservative packet.

    This provider deliberately does not infer email verification, monthly
    traffic, or behavior-based intent. Research intent signals are emitted
    only from explicit evidence on URLs returned by the dedicated intent
    search and only when an event date can be established.
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
        intent_urls = {
            result.url
            for purpose, results in searches
            if purpose == "intent"
            for result in results
            if self._same_domain(result.url, normalized_domain)
        }
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
            intent_urls=intent_urls,
        )

    @staticmethod
    def _same_domain(url: str, domain: str) -> bool:
        hostname = domain.lower().removeprefix("www.")
        result_host = urlparse(url).netloc.lower().removeprefix("www.")
        return result_host == hostname

    @classmethod
    def _select_fetch_urls(
        cls,
        searches: list[tuple[str, list[TinyFishSearchResult]]],
        domain: str,
        limit: int,
    ) -> list[str]:
        selected: list[str] = []
        seen: set[str] = set()
        # Round-robin across purposes so the dedicated intent search cannot be
        # starved by leadership/login results.
        per_purpose = {purpose: [r.url for r in results] for purpose, results in searches}
        positions = {purpose: 0 for purpose, _ in searches}
        while len(selected) < limit:
            progressed = False
            for purpose, _ in searches:
                urls = per_purpose[purpose]
                while positions[purpose] < len(urls):
                    url = urls[positions[purpose]]
                    positions[purpose] += 1
                    if cls._same_domain(url, domain) and url not in seen:
                        seen.add(url)
                        selected.append(url)
                        progressed = True
                        break
                if len(selected) == limit:
                    return selected
            if not progressed:
                break
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
        intent_urls: set[str] | None = None,
    ) -> EnrichmentPacket:
        decision_makers = cls._extract_decision_makers(fetched, observed_at)
        company_contacts = cls._extract_company_contacts(fetched, observed_at)
        employee_values = cls._employee_values(fetched)
        intent_signals = cls._extract_intent_signals(
            fetched,
            observed_at,
            intent_urls=intent_urls or {item.url for item in fetched},
        )

        notes: list[str] = [
            f"TinyFish research run fetched {len(fetched)} same-domain public URL(s).",
        ]
        if not fetched:
            notes.append("No same-domain URLs were available to fetch from TinyFish search results.")
        if len(employee_values) > 1:
            notes.append("Employee-count sources returned conflicting values; employee_count left empty.")
        if intent_signals:
            notes.append(f"Extracted {len(intent_signals)} dated intent/compliance signal(s) from intent research evidence.")
        else:
            notes.append("No dated explicit intent/compliance signal was established from intent research evidence.")

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
            intent_signals=intent_signals,
            personalization_angle=None,
            research_notes=notes + [
                f"Fetched evidence URLs: {', '.join(item.url for item in fetched)}"
                if fetched
                else "Fetched evidence URLs: none"
            ],
        )

    @classmethod
    def _extract_intent_signals(
        cls,
        fetched: list[TinyFishFetchResult],
        observed_at: datetime,
        *,
        intent_urls: set[str],
    ) -> list[IntentSignal]:
        signals: dict[tuple[str, date], IntentSignal] = {}
        for item in fetched:
            if item.url not in intent_urls:
                continue
            text = f"{item.title or ''}\n{item.text}"
            event_date = cls._event_date(item, text)
            if event_date is None:
                continue
            for signal_type, patterns, confidence in _INTENT_PATTERNS:
                match = next((pattern.search(text) for pattern in patterns if pattern.search(text)), None)
                if match is None:
                    continue
                normalized = normalize_signal(signal_type=signal_type, signal_date=event_date)
                key = (normalized.signal_type, normalized.signal_date)
                signals.setdefault(
                    key,
                    IntentSignal(
                        signal_type=normalized.signal_type,
                        signal_date=normalized.signal_date,
                        weight=normalized.weight,
                        half_life_days=normalized.half_life_days,
                        confidence=confidence,
                        evidence=[
                            Evidence(
                                claim_type="public_intent_signal",
                                claim={
                                    "signal_type": normalized.signal_type,
                                    "evidence_excerpt": cls._excerpt(text, match.start(), match.end()),
                                },
                                source_url=item.url,
                                source_type="tinyfish_fetch",
                                observed_at=observed_at,
                                event_date=event_date,
                                confidence=confidence,
                            )
                        ],
                    ),
                )
        return sorted(signals.values(), key=lambda item: (item.signal_date, item.signal_type), reverse=True)

    @staticmethod
    def _event_date(item: TinyFishFetchResult, text: str) -> date | None:
        if item.published_date:
            parsed = TinyFishEnrichmentProvider._parse_date(item.published_date)
            if parsed:
                return parsed
        match = _RE_ISO_DATE.search(text)
        if match:
            try:
                return date.fromisoformat(match.group(1))
            except ValueError:
                pass
        match = _RE_LONG_DATE.search(text)
        if match:
            cleaned = re.sub(r"(\d{1,2})(st|nd|rd|th)", r"\1", match.group(0), flags=re.I)
            cleaned = cleaned.replace(",", " ")
            for fmt in ("%B %d %Y", "%b %d %Y"):
                try:
                    return datetime.strptime(" ".join(cleaned.split()), fmt).date()
                except ValueError:
                    continue
        return None

    @staticmethod
    def _parse_date(value: str) -> date | None:
        value = value.strip()
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            pass
        for fmt in ("%Y/%m/%d", "%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _excerpt(text: str, start: int, end: int) -> str:
        excerpt = " ".join(text[max(0, start - 100) : min(len(text), end + 160)].split())
        return excerpt[:500]

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

    @staticmethod
    def _extract_company_contacts(
        fetched: list[TinyFishFetchResult], observed_at: datetime
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
