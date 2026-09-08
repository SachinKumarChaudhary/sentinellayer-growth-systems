from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from .enrichment_contracts import ContactMethod


VerificationStatus = Literal["verified", "invalid", "stale", "unknown"]


@dataclass(frozen=True)
class VerificationResult:
    status: VerificationStatus
    provider: str
    normalized_value: str
    confidence: float | None = None
    reason: str | None = None


class VerificationProvider(Protocol):
    name: str

    def verify(self, contact: ContactMethod) -> VerificationResult:
        ...


class VerificationOrchestrator:
    """Runs provider adapters without allowing them to invent contact identities."""

    def __init__(self, providers: list[VerificationProvider]) -> None:
        self.providers = providers

    def verify(self, contact: ContactMethod) -> VerificationResult:
        if not self.providers:
            return VerificationResult(
                status="unknown",
                provider="none",
                normalized_value=contact.normalized_value,
                confidence=contact.confidence,
                reason="no verification provider configured",
            )

        last: VerificationResult | None = None
        for provider in self.providers:
            try:
                result = provider.verify(contact)
            except Exception as exc:  # provider failures must not become fake verification
                last = VerificationResult(
                    status="unknown",
                    provider=provider.name,
                    normalized_value=contact.normalized_value,
                    reason=f"provider_error:{type(exc).__name__}",
                )
                continue
            if result.status in ("verified", "invalid"):
                return result
            last = result
        return last or VerificationResult(
            status="unknown",
            provider="none",
            normalized_value=contact.normalized_value,
        )


def verification_candidates(contact: ContactMethod) -> list[str]:
    """Return provider routing keys; actual API keys stay outside application data."""
    if contact.channel == "email":
        return ["qev", "email_hippo"]
    return []
