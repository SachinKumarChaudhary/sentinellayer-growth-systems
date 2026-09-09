# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sentinellayer_growth_engine.tinyfish_client import (
    TinyFishFetchResult,
    TinyFishSearchResult,
)
from sentinellayer_growth_engine.tinyfish_enrichment import TinyFishEnrichmentProvider


@dataclass
class FakeTinyFishClient:
    searches: list[tuple[str, str]]

    def search(self, query: str, *, purpose: str | None = None) -> list[TinyFishSearchResult]:
        self.searches.append((query, purpose or ""))
        return [
            TinyFishSearchResult(
                title="Leadership",
                url="https://example.com/team",
                snippet="Jane Doe — Chief Technology Officer",
            ),
            TinyFishSearchResult(
                title="External",
                url="https://other.example/team",
                snippet="should not be fetched",
            ),
        ]

    def fetch(
        self,
        urls: list[str],
        *,
        purpose: str | None = None,
        format: str = "markdown",
        include_links: bool = False,
        include_image_links: bool = False,
        include_page_metadata: bool = False,
    ) -> list[TinyFishFetchResult]:
        assert purpose and "evidence collection for company enrichment" in purpose
        assert format == "markdown"
        assert include_links is False
        assert include_page_metadata is True
        return [
            TinyFishFetchResult(
                url=urls[0],
                title="Our Team",
                text=(
                    "# Our Team\n\n## Jane Doe\nChief Technology Officer\n\n"
                    "Contact: info@example.com\n\nSign in to your account"
                ),
            )
        ]


def test_build_packet_uses_same_domain_fetched_evidence_only() -> None:
    client = FakeTinyFishClient(searches=[])
    provider = TinyFishEnrichmentProvider(client)  # type: ignore[arg-type]

    packet = provider.build_packet(
        company_id=123,
        domain="example.com",
        merchant_name="Example",
    )

    assert len(client.searches) == 8
    assert packet.company_id == 123
    assert packet.domain == "example.com"
    assert packet.merchant_name == "Example"
    assert packet.company_facts.has_login is True
    assert packet.company_facts.employee_count is None
    assert len(packet.company_contacts) == 1
    assert packet.company_contacts[0].normalized_value == "info@example.com"
    assert len(packet.decision_makers) == 1
    assert packet.decision_makers[0].full_name == "Jane Doe"
    assert packet.decision_makers[0].role_family == "engineering"
    assert packet.decision_makers[0].role_priority == 2
    assert packet.intent_signals == []


def test_search_results_can_supply_external_decision_maker_evidence() -> None:
    from sentinellayer_growth_engine.enrichment_contracts import EnrichmentPacket

    packet = EnrichmentPacket(company_id=1, domain="example.com")
    searches = [
        (
            "leadership_external",
            [
                TinyFishSearchResult(
                    title="Jane Doe | Chief Information Security Officer | Example",
                    url="https://www.linkedin.com/in/jane-doe",
                    snippet="Jane Doe — Chief Information Security Officer at Example",
                )
            ],
        )
    ]

    TinyFishEnrichmentProvider._augment_decision_makers_from_search(
        packet, searches, "example.com", datetime.now(UTC)
    )

    assert len(packet.decision_makers) == 1
    dm = packet.decision_makers[0]
    assert dm.full_name == "Jane Doe"
    assert dm.role_family == "security"
    assert dm.role_priority == 1
    assert dm.contacts[0].channel == "linkedin"
    assert dm.contacts[0].value == "https://www.linkedin.com/in/jane-doe"


def test_line_person_parser_handles_pipe_and_comma_formats() -> None:
    fetched = [
        TinyFishFetchResult(
            url="https://www.linkedin.com/in/jane-doe",
            text=(
                "Jane Doe | Chief Technology Officer | Example\n"
                "John Smith, VP Security, Example"
            ),
        )
    ]
    packet = TinyFishEnrichmentProvider._packet_from_fetched(
        company_id=1,
        domain="example.com",
        merchant_name="Example",
        fetched=fetched,
        observed_at=datetime.now(UTC),
    )
    assert {dm.full_name for dm in packet.decision_makers} == {"Jane Doe", "John Smith"}


def test_conflicting_employee_counts_are_left_empty() -> None:
    fetched = [
        TinyFishFetchResult(url="https://example.com/a", text="We have 100 employees."),
        TinyFishFetchResult(url="https://example.com/b", text="We have 150 employees."),
    ]

    packet = TinyFishEnrichmentProvider._packet_from_fetched(
        company_id=1,
        domain="example.com",
        merchant_name=None,
        fetched=fetched,
        observed_at=datetime.now(UTC),
    )

    assert packet.company_facts.employee_count is None
    assert any("conflicting values" in note for note in packet.research_notes)


def test_dated_funding_evidence_becomes_canonical_signal() -> None:
    fetched = [
        TinyFishFetchResult(
            url="https://example.com/news",
            published_date="2026-08-20",
            text="August 20, 2026 — The company raised funding to expand operations.",
        )
    ]

    packet = TinyFishEnrichmentProvider._packet_from_fetched(
        company_id=1,
        domain="example.com",
        merchant_name=None,
        fetched=fetched,
        intent_fetched=fetched,
        observed_at=datetime.now(UTC),
    )

    assert len(packet.intent_signals) == 1
    signal = packet.intent_signals[0]
    assert signal.signal_type == "funding"
    assert signal.signal_date.isoformat() == "2026-08-20"
    assert signal.weight == 3
    assert signal.half_life_days == 21
    assert signal.evidence[0].source_url == "https://example.com/news"


def test_ambiguous_keywords_without_explicit_context_do_not_create_intent() -> None:
    fetched = [
        TinyFishFetchResult(
            url="https://example.com/about",
            published_date="2026-08-20",
            text=(
                "Our platform supports funding education and security for customers."
            ),
        )
    ]

    packet = TinyFishEnrichmentProvider._packet_from_fetched(
        company_id=1,
        domain="example.com",
        merchant_name=None,
        fetched=fetched,
        intent_fetched=fetched,
        observed_at=datetime.now(UTC),
    )

    assert packet.intent_signals == []


def test_undated_intent_evidence_is_rejected() -> None:
    fetched = [
        TinyFishFetchResult(
            url="https://example.com/careers",
            text="We are hiring security engineers.",
        )
    ]

    packet = TinyFishEnrichmentProvider._packet_from_fetched(
        company_id=1,
        domain="example.com",
        merchant_name=None,
        fetched=fetched,
        intent_fetched=fetched,
        observed_at=datetime.now(UTC),
    )

    assert packet.intent_signals == []
