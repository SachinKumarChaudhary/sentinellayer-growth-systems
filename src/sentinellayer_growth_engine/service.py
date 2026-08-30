from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .engine import DueSend
from .providers import MailProvider, OutboundMessage


class MessageRenderer(Protocol):
    def render(self, send: DueSend) -> OutboundMessage:
        ...


@dataclass(frozen=True)
class ProcessResult:
    send_id: str
    accepted: bool
    provider_message_id: str | None
    error: str | None


class SendService:
    """Pure delivery orchestration for one already-claimed send."""

    def __init__(self, provider: MailProvider, renderer: MessageRenderer) -> None:
        self._provider = provider
        self._renderer = renderer

    async def process_claimed(self, claimed: DueSend) -> ProcessResult:
        message = self._renderer.render(claimed)
        result = await self._provider.send(message)
        return ProcessResult(
            send_id=claimed.send_id,
            accepted=result.accepted,
            provider_message_id=result.provider_message_id,
            error=result.error,
        )
