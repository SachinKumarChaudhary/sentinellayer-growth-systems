from dataclasses import dataclass
from typing import Protocol


class MailProviderError(Exception):
    """Base exception for expected mail-provider failures."""


class MailProviderAmbiguousError(MailProviderError):
    """The provider outcome is unknown; automatic retry may duplicate delivery."""


@dataclass(frozen=True)
class OutboundMessage:
    message_id: str
    sender: str
    recipient: str
    subject: str
    body_text: str
    headers: dict[str, str]


@dataclass(frozen=True)
class SendResult:
    accepted: bool
    provider_message_id: str | None = None
    error: str | None = None
    transient: bool = False
    provider_code: str | None = None


class DeliveryStatus:
    UNKNOWN = "unknown"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ReconciliationProvider(Protocol):
    async def lookup_delivery(self, message_id: str) -> str:
        """Return accepted/rejected/unknown using authoritative provider evidence."""
        ...


class MailProvider(Protocol):
    async def send(self, message: OutboundMessage) -> SendResult:
        ...

    async def health_check(self) -> bool:
        ...


class MockMailProvider:
    def __init__(
        self,
        *,
        accept: bool = True,
        transient: bool = False,
        provider_code: str | None = None,
    ) -> None:
        self.accept = accept
        self.transient = transient
        self.provider_code = provider_code
        self.sent: list[OutboundMessage] = []

    async def send(self, message: OutboundMessage) -> SendResult:
        if not self.accept:
            return SendResult(
                accepted=False,
                error="mock provider rejection",
                transient=self.transient,
                provider_code=self.provider_code,
            )
        self.sent.append(message)
        return SendResult(
            accepted=True,
            provider_message_id=message.message_id,
        )

    async def health_check(self) -> bool:
        return self.accept
