from __future__ import annotations

import json
from typing import Any, Self

from sentinellayer_growth_engine.email_verification_providers import QuickEmailVerificationProvider
from sentinellayer_growth_engine.enrichment_contracts import ContactMethod


class FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def test_qev_marks_safe_valid_email_verified(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "sentinellayer_growth_engine.email_verification_providers.urlopen",
        lambda request, timeout: FakeResponse(
            {"result": "valid", "safe_to_send": True, "email": "person@example.com"}
        ),
    )
    contact = ContactMethod(
        channel="email",
        value="person@example.com",
        normalized_value="person@example.com",
    )
    result = QuickEmailVerificationProvider("test-key").verify(contact)
    assert result.status == "verified"
    assert result.provider == "qev"


def test_qev_marks_invalid_email_invalid(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        "sentinellayer_growth_engine.email_verification_providers.urlopen",
        lambda request, timeout: FakeResponse(
            {"result": "invalid", "safe_to_send": False, "reason": "rejected"}
        ),
    )
    contact = ContactMethod(
        channel="email",
        value="bad@example.com",
        normalized_value="bad@example.com",
    )
    result = QuickEmailVerificationProvider("test-key").verify(contact)
    assert result.status == "invalid"
    assert result.reason == "rejected"
