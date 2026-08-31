from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .providers import MailProvider, MailProviderAmbiguousError, MailProviderError, OutboundMessage
from .retry import RetryPolicy


@dataclass(frozen=True)
class DueSend:
    send_id: str
    sender: str
    recipient: str
    subject: str
    body_text: str
    message_id: str
    attempt_count: int = 1


class SendRepository(Protocol):
    def claim_due(self, *, batch_size: int = 20, worker_id: str = "worker") -> list[DueSend]:
        ...

    def mark_sent(
        self, *, send_id: str, message_id: str, provider_message_id: str | None
    ) -> None:
        ...

    def mark_ambiguous(self, *, send_id: str, error: str) -> None:
        ...

    def mark_failed(
        self,
        *,
        send_id: str,
        error: str,
        retry_at: datetime | None,
        transient: bool = False,
        provider_code: str | None = None,
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

    async def process_due(
        self,
        *,
        batch_size: int = 20,
        worker_id: str = "worker",
        now: datetime,
    ) -> int:
        sends = self.repository.claim_due(batch_size=batch_size, worker_id=worker_id)
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

            try:
                result = await self.provider.send(message)
            except MailProviderAmbiguousError as exc:
                self.repository.mark_ambiguous(
                    send_id=send.send_id,
                    error=f"ambiguous provider outcome: {exc}",
                )
                processed += 1
                continue
            except MailProviderError as exc:
                retry_at = self.retry_policy.next_attempt_at(
                    attempt=send.attempt_count,
                    now=now,
                )
                self.repository.mark_failed(
                    send_id=send.send_id,
                    error=f"provider exception: {exc}",
                    retry_at=retry_at,
                    transient=True,
                )
                processed += 1
                continue

            if result.accepted:
                self.repository.mark_sent(
                    send_id=send.send_id,
                    message_id=send.message_id,
                    provider_message_id=result.provider_message_id,
                )
            else:
                retry_at = (
                    self.retry_policy.next_attempt_at(
                        attempt=send.attempt_count,
                        now=now,
                    )
                    if result.transient
                    else None
                )
                self.repository.mark_failed(
                    send_id=send.send_id,
                    error=result.error or "provider rejected message",
                    retry_at=retry_at,
                    transient=result.transient and retry_at is not None,
                    provider_code=result.provider_code,
                )
            processed += 1

        return processed
