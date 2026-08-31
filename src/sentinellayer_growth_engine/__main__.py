from __future__ import annotations

import asyncio
import logging
import os
import socket
import uuid

from .config import Settings
from .db import Database
from .engine import SendEngine
from .providers import MockMailProvider
from .worker import MailWorker

logger = logging.getLogger(__name__)


def build_worker(settings: Settings) -> MailWorker:
    settings.assert_safe()
    worker_id = os.getenv("SL_WORKER_ID", f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}")
    database = Database(settings.database_url, worker_id=worker_id)

    # Real SMTP integration is deliberately not enabled until its credentials
    # are explicitly configured; production must never silently fall back to mock.
    if settings.real_email_enabled:
        raise RuntimeError("real email provider is not configured yet")

    engine = SendEngine(database, MockMailProvider())
    return MailWorker(
        engine,
        tick_seconds=settings.scheduler_tick_seconds,
        worker_id=worker_id,
    )


async def run() -> None:
    settings = Settings(database_url=os.environ.get("SL_DATABASE_URL", ""))
    if not settings.database_url:
        raise RuntimeError("SL_DATABASE_URL is required")
    worker = build_worker(settings)
    stop_event = asyncio.Event()
    try:
        await worker.run(stop_event)
    finally:
        logger.info("mail worker stopped")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
