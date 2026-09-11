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
                contacts=[ContactMethod(channel="linkedin", value=linkedin, normalized_value=linkedin, source="tinyfish_search", source_url="https://www.linkedin.com/in/jane-doe/?trk=foo")],
                evidence=[
                    Evidence(claim_type="leadership_person", claim={"name": "Jane Doe", "title": "Chief Technology Officer"}, source_url="https://example.com/about/team", source_type="tinyfish_fetch", observed_at=OBSERVED_AT, confidence=0.9),
                    Evidence(claim_type="leadership_person", claim={"name": "Jane Doe", "company": "Example"}, source_url="https://www.crunchbase.com/person/jane-doe", source_type="tinyfish_search", observed_at=OBSERVED_AT, confidence=0.8),
                ],
            )
        ],
    )


def test_resolution_normalizes_linkedin_and_promotes_high_confidence_candidate() -> None:
    dm = resolve_decision_makers(_packet()).decision_makers[0]
    assert dm.contacts[0].normalized_value == "https://www.linkedin.com/in/jane-doe"
    assert dm.contacts[0].verification_status == "candidate"
    assert dm.confidence is not None and dm.confidence >= 0.90
    assert any(e.claim_type == "decision_maker_identity_resolution" for e in dm.evidence)


def test_resolution_does_not_promote_without_linkedin() -> None:
    dm = resolve_decision_makers(_packet(linkedin="not-a-linkedin-url")).decision_makers[0]
    assert dm.confidence is not None and dm.confidence < 0.90
    assert all(c.channel != "linkedin" or c.verification_status == "unknown" for c in dm.contacts)


def test_resolution_requires_person_identity_support_beyond_a_single_name_source() -> None:
    packet = EnrichmentPacket(company_id=1, domain="example.com", merchant_name="Example", decision_makers=[DecisionMaker(
        full_name="Jane Doe", title="Chief Technology Officer",
        contacts=[ContactMethod(channel="linkedin", value="https://www.linkedin.com/in/jane-doe", normalized_value="https://www.linkedin.com/in/jane-doe", source="tinyfish_search", source_url="https://www.linkedin.com/in/jane-doe")],
        evidence=[Evidence(claim_type="leadership_person", claim={"name": "Jane Doe", "title": "Chief Technology Officer"}, source_url="https://www.example.com/about/team", source_type="tinyfish_fetch", observed_at=OBSERVED_AT, confidence=0.9)],
    )])
    dm = resolve_decision_makers(packet).decision_makers[0]
    assert dm.confidence is not None and dm.confidence < 0.90


def test_resolution_keeps_same_name_different_title_candidates_distinct() -> None:
    packet = _packet()
    packet.decision_makers.append(DecisionMaker(
        full_name="Jane Doe", title="Chief Product Officer",
        contacts=[ContactMethod(channel="linkedin", value="https://www.linkedin.com/in/jane-doe-product", normalized_value="https://www.linkedin.com/in/jane-doe-product", source="tinyfish_search", source_url="https://www.linkedin.com/in/jane-doe-product")],
        evidence=[Evidence(claim_type="leadership_person", claim={"name": "Jane Doe", "title": "Chief Product Officer"}, source_url="https://www.theorg.com/org/example", source_type="tinyfish_search", observed_at=OBSERVED_AT, confidence=0.8)],
    ))
    resolved = resolve_decision_makers(packet)
    assert len(resolved.decision_makers) == 2
    assert {dm.title for dm in resolved.decision_makers} == {"Chief Technology Officer", "Chief Product Officer"}


def test_company_page_without_person_claim_does_not_count_as_person_support() -> None:
    packet = EnrichmentPacket(company_id=1, domain="example.com", merchant_name="Example", decision_makers=[DecisionMaker(
        full_name="Jane Doe", title="Chief Technology Officer",
        contacts=[ContactMethod(channel="linkedin", value="https://www.linkedin.com/in/jane-doe", normalized_value="https://www.linkedin.com/in/jane-doe", source="tinyfish_search", source_url="https://www.linkedin.com/in/jane-doe")],
        evidence=[Evidence(claim_type="company_profile", claim={"company_name": "Example", "company_domain": "example.com"}, source_url="https://example.com/about", source_type="tinyfish_fetch", observed_at=OBSERVED_AT, confidence=0.95)],
    )])
    dm = resolve_decision_makers(packet).decision_makers[0]
    assert dm.confidence is not None and dm.confidence < 0.75


def test_linkedin_slug_mismatch_blocks_outreach_ready() -> None:
    dm = resolve_decision_makers(_packet(linkedin="https://www.linkedin.com/in/john-smith")).decision_makers[0]
    assert dm.contacts[0].normalized_value == "https://www.linkedin.com/in/john-smith"
    assert dm.confidence is not None and dm.confidence < 0.90
    assert dm.contacts[0].verification_status == "candidate"


def test_linkedin_alone_does_not_prove_current_employer() -> None:
    packet = EnrichmentPacket(company_id=1, domain="example.com", merchant_name="Example", decision_makers=[DecisionMaker(
        full_name="Jane Doe", title="Chief Technology Officer",
        contacts=[ContactMethod(channel="linkedin", value="https://www.linkedin.com/in/jane-doe", normalized_value="https://www.linkedin.com/in/jane-doe", source="tinyfish_search", source_url="https://www.linkedin.com/in/jane-doe")], evidence=[]
    )])
    dm = resolve_decision_makers(packet).decision_makers[0]
    assert dm.confidence is not None and dm.confidence < 0.75


def test_person_evidence_for_wrong_company_does_not_establish_current_employer() -> None:
    packet = EnrichmentPacket(company_id=1, domain="example.com", merchant_name="Example", decision_makers=[DecisionMaker(
        full_name="Jane Doe", title="Chief Technology Officer",
        contacts=[ContactMethod(channel="linkedin", value="https://www.linkedin.com/in/jane-doe", normalized_value="https://www.linkedin.com/in/jane-doe", source="tinyfish_search", source_url="https://www.linkedin.com/in/jane-doe")],
        evidence=[
            Evidence(claim_type="leadership_person_company", claim={"name": "Jane Doe", "company_name": "Other Corp", "company_domain": "other.com"}, source_url="https://other.com/team", source_type="tinyfish_fetch", observed_at=OBSERVED_AT, confidence=0.95),
            Evidence(claim_type="leadership_person_company", claim={"name": "Jane Doe", "company_name": "Other Corp", "company_domain": "other.com"}, source_url="https://www.crunchbase.com/person/jane-doe", source_type="tinyfish_search", observed_at=OBSERVED_AT, confidence=0.9),
        ],
    )])
    dm = resolve_decision_makers(packet).decision_makers[0]
    resolution = next(e for e in dm.evidence if e.claim_type == "decision_maker_identity_resolution")
    assert resolution.claim["current_employer_confidence"] == 0.0
    assert dm.confidence is not None and dm.confidence < 0.75


def test_former_employee_evidence_is_not_outreach_ready() -> None:
    packet = _packet()
    packet.decision_makers[0].evidence[0] = Evidence(claim_type="former_leadership_person", claim={"name": "Jane Doe", "title": "Chief Technology Officer"}, source_url="https://example.com/alumni", source_type="tinyfish_fetch", observed_at=OBSERVED_AT, confidence=0.9)
    dm = resolve_decision_makers(packet).decision_makers[0]
    assert dm.confidence is not None and dm.confidence < 0.90
