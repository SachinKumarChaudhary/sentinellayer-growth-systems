from dataclasses import dataclass
from typing import Protocol


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


class MailProvider(Protocol):
    async def send(self, message: OutboundMessage) -> SendResult:
        ...

    async def health_check(self) -> bool:
        ...


class MockMailProvider:
    def __init__(self, *, accept: bool = True) -> None:
        self.accept = accept
        self.sent: list[OutboundMessage] = []

    async def send(self, message: OutboundMessage) -> SendResult:
        if not self.accept:
            return SendResult(accepted=False, error="mock provider rejection")
        self.sent.append(message)
        return SendResult(accepted=True, provider_message_id=message.message_id)

    async def health_check(self) -> bool:
        return self.accept
