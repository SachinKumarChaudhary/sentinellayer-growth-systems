from datetime import UTC, datetime

from sentinellayer_growth_engine.decision_maker_pipeline import resolve_decision_makers
from sentinellayer_growth_engine.enrichment_contracts import (
    ContactMethod,
    DecisionMaker,
    EnrichmentPacket,
    Evidence,
)


OBSERVED_AT = datetime(2026, 9, 10, tzinfo=UTC)


def _packet(*, linkedin: str = "https://www.linkedin.com/in/jane-doe/?trk=foo") -> EnrichmentPacket:
    return EnrichmentPacket(
        company_id=1,
        domain="example.com",
        merchant_name="Example",
        decision_makers=[
            DecisionMaker(
                full_name="Jane Doe",
                title="Chief Technology Officer",
                role_family="engineering",
                contacts=[
                    ContactMethod(
                        channel="linkedin",
                        value=linkedin,
                        normalized_value=linkedin,
                        source="tinyfish_search",
                        source_url="https://www.linkedin.com/in/jane-doe/?trk=foo",
                    )
                ],
                evidence=[
                    Evidence(
                        claim_type="leadership_person",
                        claim={"name": "Jane Doe", "title": "Chief Technology Officer"},
                        source_url="https://example.com/about/team",
                        source_type="tinyfish_fetch",
                        observed_at=OBSERVED_AT,
                        confidence=0.9,
                    ),
                    Evidence(
                        claim_type="leadership_person",
                        claim={"name": "Jane Doe", "company": "Example"},
                        source_url="https://www.crunchbase.com/person/jane-doe",
                        source_type="tinyfish_search",
                        observed_at=OBSERVED_AT,
                        confidence=0.8,
                    ),
                ],
            )
        ],
    )


def test_resolution_normalizes_linkedin_and_promotes_high_confidence_candidate() -> None:
    resolved = resolve_decision_makers(_packet())
    dm = resolved.decision_makers[0]

    assert dm.contacts[0].normalized_value == "https://www.linkedin.com/in/jane-doe"
    assert dm.contacts[0].verification_status == "candidate"
    assert dm.confidence is not None
    assert dm.confidence >= 0.90
    assert any(e.claim_type == "decision_maker_identity_resolution" for e in dm.evidence)


def test_resolution_does_not_promote_without_linkedin() -> None:
    packet = _packet(linkedin="not-a-linkedin-url")
    resolved = resolve_decision_makers(packet)
    dm = resolved.decision_makers[0]

    assert dm.confidence is not None
    assert dm.confidence < 0.90
    assert all(c.channel != "linkedin" or c.verification_status == "unknown" for c in dm.contacts)
