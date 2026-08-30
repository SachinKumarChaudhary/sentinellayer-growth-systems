from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .providers import MailProvider, OutboundMessage
from .retry import RetryPolicy


@dataclass(frozen=True)
class DueSend:
    send_id: str
    sender: str
    recipient: str
    subject: str
    body_text: str
    message_id: str


class SendRepository(Protocol):
    def claim_due(self, *, batch_size: int = 20) -> list[DueSend]:
        ...

    def mark_sent(
        self, *, send_id: str, message_id: str, provider_message_id: str | None
    ) -> None:
        ...

    def mark_failed(
        self, *, send_id: str, error: str, retry_at: datetime | None
    ) -> None:
        ...


class SendEngine:
    def __init__(
        self,
        repository: SendRepository,
        provider: MailProvider,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.repository = repository
        self.provider = provider
        self.retry_policy = retry_policy or RetryPolicy()

    async def process_due(self, *, batch_size: int = 20, now: datetime) -> int:
        sends = self.repository.claim_due(batch_size=batch_size)
        processed = 0

        for send in sends:
            message = OutboundMessage(
                message_id=send.message_id,
                sender=send.sender,
                recipient=send.recipient,
                subject=send.subject,
                body_text=send.body_text,
                headers={"X-SL-Send-Id": send.send_id},
            )
            result = await self.provider.send(message)

            if result.accepted:
                self.repository.mark_sent(
                    send_id=send.send_id,
                    message_id=send.message_id,
                    provider_message_id=result.provider_message_id,
                )
            else:
                self.repository.mark_failed(
                    send_id=send.send_id,
                    error=result.error or "provider rejected message",
                    retry_at=self.retry_policy.next_attempt_at(attempt=1, now=now),
                )
            processed += 1

        return processed
