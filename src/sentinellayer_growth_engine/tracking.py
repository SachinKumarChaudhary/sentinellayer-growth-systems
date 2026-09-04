from __future__ import annotations

import hashlib
import re
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

from .contracts import ContractValidationError, validate_contract

TRACKING_EVENT_SCHEMA_VERSION = "1.0"

CANONICAL_EVENT_TYPES = frozenset(
    {
        "email_opened",
        "link_clicked",
        "asset_clicked",
        "asset_viewed",
        "asset_progressed",
        "loom_started",
        "loom_progressed",
        "brief_viewed",
        "brief_progressed",
        "landing_viewed",
        "docs_viewed",
        "pricing_viewed",
        "diagnostic_started",
        "diagnostic_completed",
        "trial_signup",
        "sdk_installed",
        "evaluate_called",
        "session_started",
        "session_resumed",
        "session_ended",
    }
)

AUTOMATION_CLASSES = frozenset({"automated", "human_candidate", "unknown"})

# Strong indicators only. A missing marker does not imply human traffic.
_SCANNER_PATTERNS = (
    re.compile(r"googleimageproxy|proofpoint|mimecast|barracuda|urlscan", re.I),
    re.compile(r"headlesschrome|phantomjs|crawler|spider|bot(?:/|\\b)", re.I),
)

_TRACKING_TOKEN_BYTES = 24


@dataclass(frozen=True)
class TrafficClassification:
    classification: str
    reason: str


@dataclass(frozen=True)
class TrackingEvent:
    event_id: UUID
    schema_version: str
    event_type: str
    occurred_at: datetime
    source_system: str
    environment: str
    correlation_id: str
    confidence: float
    payload: dict[str, Any]
    account_id: str | None = None
    person_id: str | None = None
    campaign_id: str | None = None
    send_id: str | None = None
    causation_id: str | None = None

    def as_contract(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "event_id": str(self.event_id),
            "schema_version": self.schema_version,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "source_system": self.source_system,
            "environment": self.environment,
            "account_id": self.account_id,
            "person_id": self.person_id,
            "campaign_id": self.campaign_id,
            "send_id": self.send_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "confidence": self.confidence,
            "payload": self.payload,
        }
        # The shared contract permits optional IDs as nullable fields.
        validated = validate_contract("tracking_event", payload)
        return validated


def generate_tracking_token() -> str:
    """Generate an opaque, URL-safe identifier with no embedded PII."""
    return secrets.token_urlsafe(_TRACKING_TOKEN_BYTES)


def validate_destination_url(url: str) -> str:
    """Allow only absolute HTTP(S) destinations for tracked redirects."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("destination URL must be absolute HTTP(S)")
    if parsed.username or parsed.password:
        raise ValueError("destination URL must not contain embedded credentials")
    return url


def hash_ip(ip_address: str, *, secret: str) -> str:
    """Return a non-reversible keyed digest suitable for operational deduplication."""
    if not secret:
        raise ValueError("hash secret is required")
    digest = hashlib.sha256()
    digest.update(secret.encode("utf-8"))
    digest.update(b"\x00")
    digest.update(ip_address.encode("utf-8"))
    return digest.hexdigest()


def classify_traffic(
    *,
    user_agent: str | None,
    method: str = "GET",
    accept: str | None = None,
    sec_ch_ua: str | None = None,
    sec_fetch_mode: str | None = None,
    repeated_requests: int = 1,
) -> TrafficClassification:
    """Classify request traffic conservatively.

    This is a heuristic label. It does not prove a human or bot identity.
    """
    ua = user_agent or ""
    method_upper = method.upper()

    for pattern in _SCANNER_PATTERNS:
        if pattern.search(ua):
            return TrafficClassification("automated", f"user_agent:{pattern.pattern}")

    if method_upper not in {"GET", "HEAD"}:
        return TrafficClassification("unknown", "non_browser_method")

    if repeated_requests >= 20 and not sec_fetch_mode:
        return TrafficClassification("automated", "high_repeat_without_fetch_metadata")

    browser_hints = sum(
        bool(value)
        for value in (accept, sec_ch_ua, sec_fetch_mode)
    )
    if browser_hints >= 2 and user_agent:
        return TrafficClassification("human_candidate", "coherent_browser_hints")

    return TrafficClassification("unknown", "insufficient_evidence")


def default_confidence(classification: str, *, authenticated: bool = False) -> float:
    if classification == "automated":
        return 0.1
    if authenticated:
        return 0.95
    if classification == "human_candidate":
        return 0.8
    return 0.4


def build_tracking_event(
    *,
    event_type: str,
    source_system: str,
    environment: str,
    correlation_id: str,
    payload: Mapping[str, Any] | None = None,
    account_id: str | None = None,
    person_id: str | None = None,
    campaign_id: str | None = None,
    send_id: str | None = None,
    causation_id: str | None = None,
    confidence: float = 0.4,
    occurred_at: datetime | None = None,
    event_id: UUID | None = None,
) -> TrackingEvent:
    if not event_type:
        raise ContractValidationError("event_type is required")
    if event_type not in CANONICAL_EVENT_TYPES:
        raise ContractValidationError(f"unknown tracking event type: {event_type}")
    if not 0.0 <= confidence <= 1.0:
        raise ContractValidationError("confidence must be between 0 and 1")

    event = TrackingEvent(
        event_id=event_id or uuid4(),
        schema_version=TRACKING_EVENT_SCHEMA_VERSION,
        event_type=event_type,
        occurred_at=occurred_at or datetime.now(UTC),
        source_system=source_system,
        environment=environment,
        correlation_id=correlation_id,
        confidence=confidence,
        payload=dict(payload or {}),
        account_id=account_id,
        person_id=person_id,
        campaign_id=campaign_id,
        send_id=send_id,
        causation_id=causation_id,
    )
    event.as_contract()
    return event
