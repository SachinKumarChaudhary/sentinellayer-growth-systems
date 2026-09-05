from __future__ import annotations

import asyncio
from dataclasses import dataclass

from .imap_inbound import ImapInboundProvider, InboundIdentityResolver, InboundHandler


@dataclass(frozen=True)
class ConversationWorker:
    """Long-running IMAP poller; provider credentials stay outside source control."""

    provider: ImapInboundProvider
    resolver: InboundIdentityResolver
    handler: InboundHandler
    tick_seconds: int = 30

    def __post_init__(self) -> None:
        if self.tick_seconds < 1:
            raise ValueError("tick_seconds must be at least 1")

    async def run_once(self) -> list[dict[str, object]]:
        return await asyncio.to_thread(
            self.provider.poll_once,
            resolver=self.resolver,
            handler=self.handler,
        )

    async def run(self, stop_event: asyncio.Event | None = None) -> None:
        stop_event = stop_event or asyncio.Event()
        while not stop_event.is_set():
            await self.run_once()
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=self.tick_seconds)
            except TimeoutError:
                pass
