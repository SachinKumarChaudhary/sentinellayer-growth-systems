from datetime import UTC, datetime

import pytest

from sentinellayer_growth_engine.linkedin_execution import LinkedInExecutionError, execute_touchpoint
from sentinellayer_growth_engine.linkedin_outreach import LinkedInContact, build_touchpoints, validate_sequence


CONTACT = LinkedInContact(
    decision_maker_id="11111111-1111-4111-8111-111111111111",
    company_id=123,
    full_name="Jane Doe",
    title="CISO",
    linkedin_url="https://www.linkedin.com/in/jane-doe",
)
SEQUENCE_ID = "22222222-2222-4222-8222-222222222222"
NOW = datetime(2026, 9, 11, 12, tzinfo=UTC)


class FakeProvider:
    def __init__(self, capabilities: set[str], result: dict[str, object] | None = None):
        self._capabilities = capabilities
        self.result = result or {"status": "sent", "provider_reference": "li-123"}
        self.calls: list[tuple[str, str, str]] = []

    def capabilities(self) -> set[str]:
        return self._capabilities

    def send_connection_request(self, *, linkedin_url: str, message: str) -> dict[str, object]:
        self.calls.append(("connection_request", linkedin_url, message))
        return self.result

    def send_message(self, *, linkedin_url: str, message: str) -> dict[str, object]:
        self.calls.append(("message", linkedin_url, message))
        return self.result

    def observe(self, *, linkedin_url: str) -> dict[str, object]:
        return {"status": "ok", "linkedin_url": linkedin_url}


def point(action: str = "connection_request"):
    steps = validate_sequence([{"step_no": 1, "action": action, "message": "Hello Jane"}])
    return build_touchpoints(contact=CONTACT, sequence_id=SEQUENCE_ID, steps=steps, start_at=NOW)[0]


def test_unsupported_provider_capability_creates_operator_required_result_without_provider_call():
    provider = FakeProvider(set())
    result = execute_touchpoint(provider=provider, contact=CONTACT, touchpoint=point(), now=NOW)
    assert result.status == "operator_required"
    assert result.provider == "operator"
    assert result.executed_at is None
    assert provider.calls == []


def test_declared_capability_allows_real_provider_result():
    provider = FakeProvider({"linkedin.connection_request"})
    result = execute_touchpoint(provider=provider, contact=CONTACT, touchpoint=point(), now=NOW)
    assert result.status == "sent"
    assert result.provider_reference == "li-123"
    assert result.executed_at == NOW
    assert provider.calls == [("connection_request", CONTACT.linkedin_url, "Hello Jane")]


def test_provider_non_delivery_result_is_not_treated_as_sent():
    provider = FakeProvider({"linkedin.connection_request"}, {"status": "failed", "error": "blocked"})
    with pytest.raises(LinkedInExecutionError):
        execute_touchpoint(provider=provider, contact=CONTACT, touchpoint=point(), now=NOW)


def test_operator_review_never_executes_provider():
    provider = FakeProvider({"linkedin.connection_request", "linkedin.message"})
    result = execute_touchpoint(provider=provider, contact=CONTACT, touchpoint=point("operator_review"), now=NOW)
    assert result.status == "operator_required"
    assert provider.calls == []
