from __future__ import annotations

import asyncio
import logging

from .engine import SendEngine

logger = logging.getLogger(__name__)


class MailWorker:
    """Long-running scheduler for the durable send engine."""

    def __init__(
        self,
        engine: SendEngine,
        *,
        tick_seconds: int = 30,
        batch_size: int = 20,
        worker_id: str | None = None,
    ) -> None:
        if tick_seconds < 1:
            raise ValueError("tick_seconds must be at least 1")
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        self.engine = engine
        self.tick_seconds = tick_seconds
        self.batch_size = batch_size
        self.worker_id = worker_id

    async def run_once(self) -> int:
        from datetime import UTC, datetime

        return await self.engine.process_due(
            batch_size=self.batch_size,
            worker_id=self.worker_id,
            now=datetime.now(UTC),
        )

    async def run(self, stop_event: asyncio.Event | None = None) -> None:
        stop_event = stop_event or asyncio.Event()
        while not stop_event.is_set():
            try:
                processed = await self.run_once()
                if processed:
                    logger.info("processed %d scheduled sends", processed)
            except Exception:
                logger.exception("mail worker iteration failed")
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=self.tick_seconds)
            except asyncio.TimeoutError:
                pass
