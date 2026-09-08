from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .contact_verification import VerificationResult, VerificationStatus
from .enrichment_contracts import ContactMethod


@dataclass(frozen=True)
class QuickEmailVerificationProvider:
    """Adapter for QuickEmailVerification's real-time verification API."""

    api_key: str
    endpoint: str = "https://api.quickemailverification.com/v1/verify"
    timeout_seconds: float = 10.0
    name: str = "qev"

    def verify(self, contact: ContactMethod) -> VerificationResult:
        if contact.channel != "email":
            return VerificationResult(
                status="unknown",
                provider=self.name,
                normalized_value=contact.normalized_value,
                reason="provider_supports_email_only",
            )

        query = urlencode({"email": contact.normalized_value, "apikey": self.api_key})
        request = Request(
            f"{self.endpoint}?{query}",
            headers={"Accept": "application/json", "User-Agent": "sentinellayer-growth-engine/0.1.0"},
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.load(response)
        except HTTPError as exc:
            return VerificationResult(
                status="unknown",
                provider=self.name,
                normalized_value=contact.normalized_value,
                reason=f"http_error:{exc.code}",
            )
        except (URLError, TimeoutError, ValueError) as exc:
            return VerificationResult(
                status="unknown",
                provider=self.name,
                normalized_value=contact.normalized_value,
                reason=f"transport_error:{type(exc).__name__}",
            )

        if not isinstance(payload, dict):
            return VerificationResult(
                status="unknown",
                provider=self.name,
                normalized_value=contact.normalized_value,
                reason="invalid_provider_payload",
            )

        result = str(payload.get("result", "")).lower()
        safe_to_send = payload.get("safe_to_send")
        if result == "invalid":
            status: VerificationStatus = "invalid"
        elif result == "valid" and safe_to_send is True:
            status = "verified"
        elif result in {"valid", "unknown", "unverifiable", "catch_all"}:
            status = "unknown"
        else:
            status = "unknown"

        confidence = 0.95 if status == "verified" else 0.95 if status == "invalid" else 0.4
        reason = str(payload.get("reason") or payload.get("message") or result or "no_result")
        normalized = str(payload.get("email") or contact.normalized_value).strip().lower()
        return VerificationResult(
            status=status,
            provider=self.name,
            normalized_value=normalized,
            confidence=confidence,
            reason=reason,
        )
