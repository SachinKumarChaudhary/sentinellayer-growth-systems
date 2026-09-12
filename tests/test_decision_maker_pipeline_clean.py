from datetime import UTC, datetime

from sentinellayer_growth_engine.decision_maker_pipeline import resolve_decision_makers
from sentinellayer_growth_engine.enrichment_contracts import ContactMethod, DecisionMaker, EnrichmentPacket, Evidence

OBSERVED_AT = datetime(2026, 9, 10, tzinfo=UTC)


def packet(linkedin: str = "https://www.linkedin.com/in/jane-doe/?trk=foo") -> EnrichmentPacket:
    return EnrichmentPacket(
        company_id=1,
        domain="example.com",
        merchant_name="Example",
        decision_makers=[DecisionMaker(
            full_name="Jane Doe",
            title="Chief Technology Officer",
            role_family="engineering",
            contacts=[ContactMethod(channel="linkedin", value=linkedin, normalized_value=linkedin, source="tinyfish_search", source_url=linkedin)],
            evidence=[
                Evidence(claim_type="leadership_person", claim={"name": "Jane Doe", "title": "Chief Technology Officer"}, source_url="https://example.com/about/team", source_type="tinyfish_fetch", observed_at=OBSERVED_AT, confidence=0.9),
                Evidence(claim_type="leadership_person", claim={"name": "Jane Doe", "company": "Example"}, source_url="https://www.crunchbase.com/person/jane-doe", source_type="tinyfish_search", observed_at=OBSERVED_AT, confidence=0.8),
            ],
        )],
    )


def test_high_confidence_person_gets_canonical_linkedin_candidate():
    dm = resolve_decision_makers(packet()).decision_makers[0]
    assert dm.contacts[0].normalized_value == "https://www.linkedin.com/in/jane-doe"
    assert dm.contacts[0].verification_status == "candidate"
    assert dm.confidence is not None and dm.confidence >= 0.90


def test_linkedin_alone_does_not_prove_current_employer():
    p = packet()
    p.decision_makers[0].evidence = []
    dm = resolve_decision_makers(p).decision_makers[0]
    assert dm.confidence is not None and dm.confidence < 0.75


def test_wrong_company_evidence_is_not_current_employer_support():
    p = packet()
    p.decision_makers[0].evidence = [
        Evidence(claim_type="leadership_person_company", claim={"name": "Jane Doe", "company_domain": "other.com"}, source_url="https://other.com/team", source_type="tinyfish_fetch", observed_at=OBSERVED_AT, confidence=0.95),
        Evidence(claim_type="leadership_person_company", claim={"name": "Jane Doe", "company_domain": "other.com"}, source_url="https://www.crunchbase.com/person/jane-doe", source_type="tinyfish_search", observed_at=OBSERVED_AT, confidence=0.9),
    ]
    dm = resolve_decision_makers(p).decision_makers[0]
    resolution = next(e for e in dm.evidence if e.claim_type == "decision_maker_identity_resolution")
    assert resolution.claim["current_employer_confidence"] == 0.0


def test_former_employee_is_not_outreach_ready():
    p = packet()
    p.decision_makers[0].evidence[0] = Evidence(claim_type="former_leadership_person", claim={"name": "Jane Doe", "title": "Chief Technology Officer"}, source_url="https://example.com/alumni", source_type="tinyfish_fetch", observed_at=OBSERVED_AT, confidence=0.9)
    dm = resolve_decision_makers(p).decision_makers[0]
    resolution = next(e for e in dm.evidence if e.claim_type == "decision_maker_identity_resolution")
    assert resolution.claim["outreach_status"] != "outreach_ready"
