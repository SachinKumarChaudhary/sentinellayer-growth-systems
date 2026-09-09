# ruff: noqa: E501

from __future__ import annotations

import re
from datetime import UTC, date, datetime
from urllib.parse import urlparse

from .enrichment_contracts import (
    CompanyContact,
    CompanyFacts,
    ContactMethod,
    DecisionMaker,
    EnrichmentPacket,
    Evidence,
    IntentSignal,
)
from .intent_normalization import normalize_signal
from .tinyfish_client import TinyFishClient, TinyFishFetchResult, TinyFishSearchResult

_RE_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
_RE_EMPLOYEES = re.compile(
    r"\b(\d{1,3}(?:,\d{3})*|\d+)\s+employees\b", re.IGNORECASE
)
_RE_ISO_DATE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_RE_US_DATE = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{1,2},\s+20\d{2}\b",
    re.IGNORECASE,
)
_RE_HEADING_PERSON = re.compile(
    r"(?:^|\n)#{2,4}\s+([A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,3})"
    r"\s*\n\s*([A-Z][A-Za-z&/ ,.'’()-]{2,100})\s*(?=\n|$)",
)
_RE_DASH_PERSON = re.compile(
    r"\b([A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,3})\s*[—–-]\s*"
    r"((?:Chief|President|Founder|Co-Founder|VP|Vice President|Head|Director|"
    r"SVP|EVP|CTO|CISO|CFO|COO|CEO)[^\n.;]{2,100})",
)
_RE_LINE_PERSON = re.compile(
    r"(?m)\b([A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){1,3})\s*(?:\||,)\s*"
    r"((?:Chief|President|Founder|Co-Founder|VP|Vice President|Head|Director|"
    r"SVP|EVP|CTO|CISO|CFO|COO|CEO|Officer|Security|Technology|Engineering|Product|"
    r"Risk|Fraud|Information)[^\n|.;]{2,120})"
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

# These patterns require an explicit trigger plus relevant context. They are
# intentionally narrower than the aliases used by the downstream normalizer.
_INTENT_CONTEXT: tuple[tuple[str, tuple[tuple[str, ...], ...]], ...] = (
    ("funding", (("raised", "funding"), ("raised", "financing"),
                 ("funding round",), ("series a",), ("series b",), ("series c",))),
    ("new_c_suite", (("appointed", "ceo"), ("appointed", "cto"),
                      ("appointed", "cfo"), ("appointed", "ciso"),
                      ("named", "ceo"), ("joined as", "ceo"),
                      ("new ceo",), ("new cto",), ("new cfo",))),
    ("security_hiring", (("hiring", "security"), ("hiring", "cybersecurity"),
                          ("hiring", "fraud"), ("hiring", "risk"),
                          ("security engineer",), ("fraud analyst",))),
    ("tech_migration", (("migrated", "platform"), ("migration", "platform"),
                         ("replatform",), ("technology migration",),
                         ("migrating to", "shopify"), ("migrating to", "next.js"))),
    ("new_market", (("launched in", "market"), ("expanded into", "market"),
                     ("entered", "market"), ("international expansion",),
                     ("launched in", "europe"), ("expanded to", "india"))),
    ("regulated_expansion", (("regulated", "expansion"), ("regulatory", "launch"),
                              ("compliance", "expansion"),
                              ("new regulated category",))),
    ("franchise_launch", (("new franchise",), ("first franchise",),
                           ("franchise", "opened"), ("franchise", "launch"))),
    ("award", (("won", "award"), ("named", "award"), ("inc. 5000",),
                ("inc 5000",), ("future50",), ("forbes",))),
    ("seasonal_window", (("seasonal", "campaign"), ("holiday", "campaign"),
                          ("black friday",), ("cyber monday",))),
    ("pci", (("pci dss",), ("pci 4.0",))),
    ("gdpr", (("gdpr",),)),
    ("dpdp", (("dpdp act",), ("digital personal data protection",))),
    ("soc2_requirement", (("soc 2", "requirement"), ("soc2", "procurement"),
                           ("vendor security review",))),
    ("ftc_click_to_cancel", (("ftc", "click to cancel"), ("click-to-cancel",))),
    ("ca_breach", (("california breach",), ("security breach",),
                    ("data breach", "california"), ("sb 362",))),
)


class TinyFishEnrichmentProvider:
    """Collect public evidence with TinyFish and build a conservative packet."""

    SEARCH_PURPOSES: tuple[tuple[str, str], ...] = (
        ("leadership", "leadership executive management team founder CEO CTO CISO"),
        ("decision_makers", "CEO CTO CIO CISO VP security fraud risk product engineering founder"),
        ("leadership_external", "executive team leadership founder CEO CTO CISO site:linkedin.com/in"),
        ("login", "customer login sign in account authentication"),
        ("commerce", "ecommerce store checkout Shopify customer account"),
        ("security", "fraud account takeover security risk cybersecurity"),
        ("technology", "technology engineering product platform architecture replatform migration"),
        ("intent", "funding hiring acquisition expansion new market technology migration security breach"),
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

        company_label = merchant_name or normalized_domain
        searches: list[tuple[str, list[TinyFishSearchResult]]] = []
        for purpose, suffix in self.SEARCH_PURPOSES:
            query = f'"{company_label}" {normalized_domain} {suffix}'
            results = self._client.search(query, purpose=purpose)
            searches.append((purpose, results))

        urls = self._select_fetch_urls(searches, normalized_domain, max_fetch_urls)
        fetched = self._client.fetch(
            urls,
            purpose="evidence collection for company enrichment; prioritize leadership, company facts, security and dated intent evidence",
            include_links=False,
            include_page_metadata=True,
        )
        intent_urls = {
            result.url
            for purpose, results in searches
            if purpose == "intent"
            for result in results
        }
        intent_fetched = [item for item in fetched if item.url in intent_urls]
        packet = self._packet_from_fetched(
            company_id=company_id,
            domain=normalized_domain,
            merchant_name=merchant_name,
            fetched=fetched,
            intent_fetched=intent_fetched,
            observed_at=datetime.now(UTC),
        )
        self._augment_decision_makers_from_search(
            packet,
            searches,
            normalized_domain,
            company_label,
            datetime.now(UTC),
        )
        return packet

    @staticmethod
    def _select_fetch_urls(
        searches: list[tuple[str, list[TinyFishSearchResult]]],
        domain: str,
        limit: int,
    ) -> list[str]:
        hostname = domain.lower().removeprefix("www.")
        selected: list[str] = []
        seen: set[str] = set()

        def host_score(url: str) -> int:
            parsed = urlparse(url)
            host = parsed.netloc.lower().removeprefix("www.")
            if host == hostname:
                return 0
            if host == "linkedin.com" or host.endswith(".linkedin.com"):
                return 1
            if host in {"crunchbase.com", "theorg.com", "forbes.com", "sec.gov"}:
                return 2
            return 3

        # Guarantee one high-value result per research purpose, preferring
        # official pages, then public professional/company profiles.
        for _, results in searches:
            candidates = sorted(
                (r for r in results if r.url not in seen),
                key=lambda r: (host_score(r.url), len(r.url)),
            )
            for result in candidates:
                if host_score(result.url) >= 3:
                    continue
                seen.add(result.url)
                selected.append(result.url)
                break
            if len(selected) == limit:
                return selected

        # Fill remaining slots from all high-quality results.
        for _, results in searches:
            for result in sorted(results, key=lambda r: (host_score(r.url), len(r.url))):
                if result.url in seen or host_score(result.url) >= 3:
                    continue
                seen.add(result.url)
                selected.append(result.url)
                if len(selected) == limit:
                    return selected
        return selected[:limit]

    @classmethod
    def _packet_from_fetched(
        cls,
        *,
        company_id: int,
        domain: str,
        merchant_name: str | None,
        fetched: list[TinyFishFetchResult],
        observed_at: datetime,
        intent_fetched: list[TinyFishFetchResult] | None = None,
    ) -> EnrichmentPacket:
        decision_makers = cls._extract_decision_makers(fetched, observed_at)
        company_contacts = cls._extract_company_contacts(fetched, observed_at)
        employee_values = cls._employee_values(fetched)
        intent_signals = cls._extract_intent_signals(
            intent_fetched if intent_fetched is not None else fetched,
            observed_at,
        )

        notes = [f"TinyFish research run fetched {len(fetched)} public evidence URL(s)."]
        if not fetched:
            notes.append("No usable public URLs were available to fetch from TinyFish search results.")
        if len(employee_values) > 1:
            notes.append("Employee-count sources returned conflicting values; employee_count left empty.")
        if intent_fetched is not None and not intent_fetched:
            notes.append("No dedicated intent-search URL was fetched; no intent signal was inferred.")
        elif not intent_signals:
            notes.append("Dedicated intent evidence contained no explicit dated canonical trigger.")

        employee_count = next(iter(employee_values)) if len(employee_values) == 1 else None
        facts = CompanyFacts(
            employee_count=employee_count,
            monthly_sessions=cls._monthly_sessions(fetched),
            has_login=cls._has_login(fetched),
            vertical=cls._extract_vertical(fetched),
            ownership_type=cls._extract_ownership_type(fetched),
            india_bridge=cls._india_bridge(fetched),
            data_sensitivity=cls._extract_data_sensitivity(fetched),
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
    ) -> list[IntentSignal]:
        signals: dict[tuple[str, date, str], IntentSignal] = {}
        for item in fetched:
            signal_date = cls._recover_event_date(item)
            if signal_date is None:
                continue
            text = " ".join(item.text.casefold().split())
            for signal_type, contexts in _INTENT_CONTEXT:
                if not any(all(term in text for term in context) for context in contexts):
                    continue
                canonical = normalize_signal(
                    signal_type=signal_type,
                    signal_date=signal_date,
                )
                matched_context = next(
                    context for context in contexts if all(term in text for term in context)
                )
                evidence = Evidence(
                    claim_type="public_intent_signal",
                    claim={
                        "signal_type": canonical.signal_type,
                        "matched_terms": matched_context,
                    },
                    source_url=item.url,
                    source_type="tinyfish_fetch",
                    observed_at=observed_at,
                    event_date=signal_date,
                    confidence=0.85,
                )
                key = (canonical.signal_type, canonical.signal_date, item.url)
                signals.setdefault(
                    key,
                    IntentSignal(
                        signal_type=canonical.signal_type,
                        signal_date=canonical.signal_date,
                        weight=canonical.weight,
                        half_life_days=canonical.half_life_days,
                        confidence=0.85,
                        evidence=[evidence],
                    ),
                )
        return sorted(
            signals.values(),
            key=lambda item: (item.signal_date, item.signal_type),
            reverse=True,
        )

    @staticmethod
    def _recover_event_date(item: TinyFishFetchResult) -> date | None:
        if item.published_date:
            try:
                return date.fromisoformat(item.published_date.strip()[:10])
            except ValueError:
                pass
        match = _RE_ISO_DATE.search(item.text)
        if match:
            return date.fromisoformat(match.group(1))
        match = _RE_US_DATE.search(item.text)
        if match:
            for fmt in ("%B %d, %Y", "%b %d, %Y"):
                try:
                    return datetime.strptime(match.group(0), fmt).date()
                except ValueError:
                    continue
        return None

    @staticmethod
    def _has_login(fetched: list[TinyFishFetchResult]) -> bool:
        terms = ("sign in", "log in", "login", "create an account", "customer account")
        return any(
            any(term in f"{item.title or ''}\n{item.text}".lower() for term in terms)
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
                        evidence=[Evidence(
                            claim_type="public_company_email",
                            claim={"email": email},
                            source_url=item.url,
                            source_type="tinyfish_fetch",
                            observed_at=observed_at,
                            confidence=1.0,
                        )],
                    ),
                )
        return list(contacts.values())

    @staticmethod
    def _monthly_sessions(fetched: list[TinyFishFetchResult]) -> int | None:
        pattern = re.compile(
            r"\b([0-9]+(?:,[0-9]{3})*|[0-9]+(?:\.[0-9]+)?[KMB]?)\s+"
            r"(?:monthly\s+)?(?:visits|sessions|visitors)\b",
            re.IGNORECASE,
        )
        values: set[int] = set()
        for item in fetched:
            for raw in pattern.findall(item.text):
                token = raw.replace(",", "").upper()
                multiplier = 1
                if token.endswith("K"):
                    multiplier, token = 1_000, token[:-1]
                elif token.endswith("M"):
                    multiplier, token = 1_000_000, token[:-1]
                elif token.endswith("B"):
                    multiplier, token = 1_000_000_000, token[:-1]
                values.add(int(float(token) * multiplier))
        return next(iter(values)) if len(values) == 1 else None

    @staticmethod
    def _extract_vertical(fetched: list[TinyFishFetchResult]) -> str | None:
        labels = (
            ("cybersecurity", "cybersecurity"),
            ("cyber security", "cybersecurity"),
            ("fintech", "fintech"),
            ("financial services", "financial_services"),
            ("ecommerce", "ecommerce"),
            ("e-commerce", "ecommerce"),
            ("healthcare", "healthcare"),
            ("saas", "saas"),
            ("gaming", "gaming"),
            ("media", "media"),
            ("education", "education"),
            ("travel", "travel"),
        )
        text = " ".join(item.text.casefold() for item in fetched)
        matches = [value for needle, value in labels if re.search(rf"\b{re.escape(needle)}\b", text)]
        return matches[0] if matches else None

    @staticmethod
    def _extract_ownership_type(fetched: list[TinyFishFetchResult]) -> str | None:
        text = " ".join(item.text.casefold() for item in fetched)
        if "publicly traded" in text or "listed on" in text or "nasdaq" in text or "nyse" in text:
            return "public_company"
        if "private company" in text or "privately held" in text:
            return "privately_held"
        if "family-owned" in text or "family owned" in text:
            return "family_owned"
        return None

    @staticmethod
    def _india_bridge(fetched: list[TinyFishFetchResult]) -> bool:
        text = " ".join(item.text.casefold() for item in fetched)
        return any(term in text for term in ("india office", "india-based", "based in india", "bengaluru", "bangalore", "hyderabad", "mumbai", "delhi"))

    @staticmethod
    def _extract_data_sensitivity(fetched: list[TinyFishFetchResult]) -> str | None:
        text = " ".join(item.text.casefold() for item in fetched)
        for needle, value in (
            ("payment", "financial"),
            ("credit card", "financial"),
            ("financial data", "financial"),
            ("health record", "health"),
            ("medical record", "health"),
            ("identity verification", "identity"),
            ("personal data", "personal"),
            ("customer data", "customer"),
        ):
            if needle in text:
                return value
        return None

    @classmethod
    def _augment_decision_makers_from_search(
        cls,
        packet: EnrichmentPacket,
        searches: list[tuple[str, list[TinyFishSearchResult]]],
        domain: str,
        company_label: str,
        observed_at: datetime,
    ) -> None:
        found: dict[tuple[str, str], DecisionMaker] = {
            (dm.full_name.casefold(), (dm.title or "").casefold()): dm
            for dm in packet.decision_makers
        }
        for purpose, results in searches:
            if purpose not in {"leadership", "decision_makers", "leadership_external"}:
                continue
            for result in results:
                result_text = result.snippet + "\n" + result.title
                if purpose == "leadership_external":
                    identity = (
                        company_label.casefold(),
                        domain.casefold().removeprefix("www."),
                    )
                    lowered = result_text.casefold()
                    if not any(token in lowered for token in identity):
                        continue
                candidate = cls._extract_decision_makers_from_text(
                    result_text, result.url, observed_at, "tinyfish_search"
                )
                for dm in candidate:
                    key = (dm.full_name.casefold(), (dm.title or "").casefold())
                    existing = found.get(key)
                    if existing is not None:
                        continue
                    found[key] = dm
        ranked = sorted(found.values(), key=lambda item: (item.role_priority or 99, item.full_name))
        packet.decision_makers = ranked[:10]

    @classmethod
    def _extract_decision_makers_from_text(
        cls, text: str, source_url: str, observed_at: datetime, source_type: str
    ) -> list[DecisionMaker]:
        pairs = list(_RE_HEADING_PERSON.findall(text)) + list(_RE_DASH_PERSON.findall(text)) + list(_RE_LINE_PERSON.findall(text))
        found: list[DecisionMaker] = []
        for name, title in pairs:
            clean_name = " ".join(name.split()).strip(" -—–|,")
            clean_title = " ".join(title.split()).strip(" -—–|,")
            if len(clean_name.split()) < 2:
                continue
            family, priority = cls._role_family(clean_title)
            if family is None:
                continue
            found.append(
                DecisionMaker(
                    full_name=clean_name,
                    title=clean_title,
                    role_family=family,
                    role_priority=priority,
                    rationale="Public professional or company-source evidence associated with the company.",
                    confidence=0.9 if source_type == "tinyfish_fetch" else 0.75,
                    contacts=cls._social_contact(
                        source_url, observed_at, clean_name, text, source_type
                    ),
                    evidence=[
                        Evidence(
                            claim_type="public_decision_maker",
                            claim={"name": clean_name, "title": clean_title},
                            source_url=source_url,
                            source_type=source_type,
                            observed_at=observed_at,
                            confidence=0.9 if source_type == "tinyfish_fetch" else 0.75,
                        )
                    ],
                )
            )
        return found

    @staticmethod
    def _social_contact(
        source_url: str,
        observed_at: datetime,
        name: str,
        text: str,
        source_type: str,
    ) -> list[ContactMethod]:
        parsed = urlparse(source_url)
        host = parsed.netloc.lower().removeprefix("www.")
        contacts: list[ContactMethod] = []
        if host == "linkedin.com" or host.endswith(".linkedin.com"):
            contacts.append(
                ContactMethod(
                    channel="linkedin",
                    value=source_url,
                    normalized_value=source_url,
                    source="tinyfish_search",
                    source_url=source_url,
                    confidence=0.9,
                )
            )
        generic_prefixes = {
            "info",
            "hello",
            "support",
            "sales",
            "contact",
            "careers",
            "hr",
            "team",
            "press",
        }
        for email in _RE_EMAIL.findall(text):
            local_part = email.split("@", 1)[0].casefold()
            if local_part in generic_prefixes:
                continue
            contacts.append(
                ContactMethod(
                    channel="email",
                    value=email,
                    normalized_value=email.casefold(),
                    source=source_type,
                    source_url=source_url,
                    confidence=0.75,
                )
            )
        return contacts

    @classmethod
    def _extract_decision_makers(
        cls, fetched: list[TinyFishFetchResult], observed_at: datetime
    ) -> list[DecisionMaker]:
        found: dict[tuple[str, str], DecisionMaker] = {}
        for item in fetched:
            for dm in cls._extract_decision_makers_from_text(
                item.text,
                item.final_url or item.url,
                observed_at,
                "tinyfish_fetch",
            ):
                key = (dm.full_name.casefold(), (dm.title or "").casefold())
                found[key] = dm
        return sorted(
            found.values(),
            key=lambda item: (item.role_priority or 99, item.full_name),
        )
    @staticmethod
    def _role_family(title: str) -> tuple[str | None, int | None]:
        lowered = title.casefold()
        for needle, family, priority in _ROLE_FAMILIES:
            if needle in lowered:
                return family, priority
        return None, None
