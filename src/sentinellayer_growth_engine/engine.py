from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .providers import MailProvider, OutboundMessage


@dataclass(frozen=True)
class DueSend:
    send_id: str
    sender: str
    recipient: str
    subject: str
    body_text: str
    message_id: str


class SendRepository(Protocol):
    async def claim_due(self, *, worker_id: str, now: datetime) -> list[DueSend]:
        ...

    async def mark_sent(
        self, *, send_id: str, message_id: str, provider_message_id: str | None
    ) -> None:
        ...

    async def mark_failed(self, *, send_id: str, error: str) -> None:
        ...


class SendEngine:
    def __init__(self, repository: SendRepository, provider: MailProvider) -> None:
        self.repository = repository
        self.provider = provider

    async def process_due(self, *, worker_id: str, now: datetime) -> int:
        sends = await self.repository.claim_due(worker_id=worker_id, now=now)
        processed = 0

        for send in sends:
            message = OutboundMessage(
                message_id=send.message_id,
                sender=send.sender,
                recipient=send.recipient,
                subject=send.subject,
                body_text=send.body_text,
                headers={
                    "X-SL-Send-Id": send.send_id,
                },
            )
            result = await self.provider.send(message)
            if result.accepted:
                await self.repository.mark_sent(
                    send_id=send.send_id,
                    message_id=send.message_id,
                    provider_message_id=result.provider_message_id,
                )
            else:
                await self.repository.mark_failed(
                    send_id=send.send_id,
                    error=result.error or "provider rejected message",
                )
            processed += 1

        return processed
