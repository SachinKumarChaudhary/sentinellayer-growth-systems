from __future__ import annotations

from dataclasses import dataclass

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
        assert purpose == "evidence collection for company enrichment"
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

    assert len(client.searches) == 5
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
        observed_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
    )

    assert packet.company_facts.employee_count is None
    assert any("conflicting values" in note for note in packet.research_notes)
