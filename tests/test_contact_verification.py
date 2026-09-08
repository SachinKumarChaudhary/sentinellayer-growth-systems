from sentinellayer_growth_engine.contact_verification import (
    VerificationOrchestrator,
    verification_candidates,
)
from sentinellayer_growth_engine.enrichment_contracts import ContactMethod


def test_email_uses_qev_and_email_hippo_candidates() -> None:
    contact = ContactMethod(
        channel="email",
        value="person@example.com",
        normalized_value="person@example.com",
    )
    assert verification_candidates(contact) == ["qev", "email_hippo"]


def test_missing_providers_never_claim_verification() -> None:
    contact = ContactMethod(
        channel="email",
        value="person@example.com",
        normalized_value="person@example.com",
    )
    result = VerificationOrchestrator([]).verify(contact)
    assert result.status == "unknown"
    assert result.provider == "none"
