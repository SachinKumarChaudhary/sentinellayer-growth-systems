from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from sentinellayer_growth_engine.contracts import ContractValidationError
from sentinellayer_growth_engine.tracking import (
    AUTOMATION_CLASSES,
    CANONICAL_EVENT_TYPES,
    build_tracking_event,
    classify_traffic,
    default_confidence,
    generate_tracking_token,
    hash_ip,
    validate_destination_url,
)


def test_generate_tracking_token_is_opaque_and_unique() -> None:
    first = generate_tracking_token()
    second = generate_tracking_token()

    assert first != second
    assert len(first) >= 32
    assert "@" not in first


def test_destination_url_requires_https() -> None:
    assert validate_destination_url("https://example.com/path") == "https://example.com/path"

    assert validate_destination_url("http://example.com/path") == "http://example.com/path"

    with pytest.raises(ValueError):
        validate_destination_url("javascript:alert(1)")

    with pytest.raises(ValueError):
        validate_destination_url("https://user:password@example.com/path")


def test_hash_ip_requires_secret_and_is_stable() -> None:
    with pytest.raises(ValueError):
        hash_ip("203.0.113.10", secret="")

    first = hash_ip("203.0.113.10", secret="test-secret")
    second = hash_ip("203.0.113.10", secret="test-secret")
    other = hash_ip("203.0.113.11", secret="test-secret")

    assert first == second
    assert first != other
    assert len(first) == 64


def test_scanner_is_classified_conservatively() -> None:
    result = classify_traffic(user_agent="Mozilla/5.0 GoogleImageProxy", accept="*/*")

    assert result.classification == "automated"
    assert result.reason.startswith("user_agent:")


def test_coherent_browser_request_is_human_candidate() -> None:
    result = classify_traffic(
        user_agent="Mozilla/5.0 Chrome/140.0 Safari/537.36",
        accept="text/html",
        sec_ch_ua='"Chromium";v="140"',
        sec_fetch_mode="navigate",
    )

    assert result.classification == "human_candidate"


def test_unknown_request_does_not_become_human_by_default() -> None:
    result = classify_traffic(user_agent=None)
    assert result.classification == "unknown"


def test_automation_classification_values_are_closed() -> None:
    assert AUTOMATION_CLASSES == {"automated", "human_candidate", "unknown"}


def test_default_confidence_reflects_evidence_quality() -> None:
    assert default_confidence("automated") < default_confidence("unknown")
    assert default_confidence("human_candidate") > default_confidence("unknown")
    assert default_confidence("unknown", authenticated=True) == 0.95


def test_build_tracking_event_validates_and_preserves_identity() -> None:
    when = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    event = build_tracking_event(
        event_type="pricing_viewed",
        source_system="tracking",
        environment="development",
        correlation_id="corr-123",
        account_id="account-1",
        person_id="person-1",
        campaign_id="campaign-1",
        send_id="send-1",
        confidence=0.8,
        occurred_at=when,
        payload={"path": "/pricing"},
    )

    assert isinstance(event.event_id, UUID)
    contract = event.as_contract()
    assert contract["event_id"] == str(event.event_id)
    assert contract["account_id"] == "account-1"
    assert contract["person_id"] == "person-1"
    assert contract["event_type"] == "pricing_viewed"
    assert contract["confidence"] == 0.8


def test_unknown_event_type_fails_closed() -> None:
    with pytest.raises(ContractValidationError):
        build_tracking_event(
            event_type="invented_event",
            source_system="tracking",
            environment="development",
            correlation_id="corr-123",
        )


def test_confidence_bounds_fail_closed() -> None:
    for confidence in (-0.01, 1.01):
        with pytest.raises(ContractValidationError):
            build_tracking_event(
                event_type="pricing_viewed",
                source_system="tracking",
                environment="development",
                correlation_id="corr-123",
                confidence=confidence,
            )


def test_canonical_event_taxonomy_is_nonempty() -> None:
    assert "link_clicked" in CANONICAL_EVENT_TYPES
    assert "loom_progressed" in CANONICAL_EVENT_TYPES
    assert "trial_signup" in CANONICAL_EVENT_TYPES
