from datetime import datetime, timezone

from sentinellayer_growth_engine.engine import DueSend, SendEngine
from sentinellayer_growth_engine.providers import MockMailProvider
from sentinellayer_growth_engine.scheduler import Scheduler, SchedulerConfig


class FakeRepository:
    async def claim_due(self, *, worker_id: str, now: datetime) -> list[DueSend]:
        return []

    async def mark_sent(self, *, send_id: str, message_id: str, provider_message_id: str | None) -> None:
        raise AssertionError("no sends expected")

    async def mark_failed(self, *, send_id: str, error: str) -> None:
        raise AssertionError("no sends expected")


async def test_scheduler_delegates_to_engine() -> None:
    engine = SendEngine(FakeRepository(), MockMailProvider())
    scheduler = Scheduler(engine, SchedulerConfig(worker_id="worker-test"))
    assert await scheduler.tick(now=datetime.now(timezone.utc)) == 0
