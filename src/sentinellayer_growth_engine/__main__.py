from __future__ import annotations

import asyncio
import logging
import os
import socket
import uuid

from .config import Settings
from .db import Database
from .engine import SendEngine
from .providers import MailProvider, MockMailProvider
from .smtp import SmtpMailProvider
from .worker import MailWorker

logger = logging.getLogger(__name__)


def build_worker(settings: Settings) -> MailWorker:
    settings.assert_safe()
    worker_id = os.getenv("SL_WORKER_ID", f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}")
    database = Database(settings.database_url, worker_id=worker_id)

    if settings.real_email_enabled:
        provider: MailProvider = SmtpMailProvider(
            host=settings.smtp_host or "",
            port=settings.smtp_port,
            username=settings.smtp_username or "",
            password=settings.smtp_password or "",
            timeout_seconds=settings.smtp_timeout_seconds,
        )
    else:
        provider = MockMailProvider()

    engine = SendEngine(database, provider)
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
