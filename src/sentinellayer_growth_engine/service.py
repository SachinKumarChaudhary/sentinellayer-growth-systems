from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .db import ClaimedSend, Database
from .providers import MailProvider, OutboundMessage


class MessageRenderer(Protocol):
    def render(self, send: ClaimedSend) -> OutboundMessage:
        ...


@dataclass(frozen=True)
class ProcessResult:
    send_id: str
    accepted: bool
    provider_message_id: str | None
    error: str | None


class SendService:
    def __init__(self, db: Database, provider: MailProvider, renderer: MessageRenderer) -> None:
        self._db = db
        self._provider = provider
        self._renderer = renderer

    async def process_claimed(self, claimed: ClaimedSend) -> ProcessResult:
        message = self._renderer.render(claimed)
        result = await self._provider.send(message)
        return ProcessResult(
            send_id=claimed.send_id,
            accepted=result.accepted,
            provider_message_id=result.provider_message_id,
            error=result.error,
        )
