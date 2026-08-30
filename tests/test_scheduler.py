from datetime import UTC, datetime

from sentinellayer_growth_engine.engine import DueSend, SendEngine
from sentinellayer_growth_engine.providers import MockMailProvider
from sentinellayer_growth_engine.scheduler import Scheduler, SchedulerConfig


class FakeRepository:
    def __init__(self) -> None:
        self.worker_id: str | None = None
        self.batch_size: int | None = None

    def claim_due(
        self, *, batch_size: int = 20, worker_id: str = "worker"
    ) -> list[DueSend]:
        self.worker_id = worker_id
        self.batch_size = batch_size
        return []

    def mark_sent(
        self, *, send_id: str, message_id: str, provider_message_id: str | None
    ) -> None:
        raise AssertionError("no sends expected")

    def mark_failed(
        self,
        *,
        send_id: str,
        error: str,
        retry_at: datetime | None,
        transient: bool = False,
        provider_code: str | None = None,
    ) -> None:
        raise AssertionError("no sends expected")


async def test_scheduler_delegates_worker_identity_and_batch_size() -> None:
    repo = FakeRepository()
    engine = SendEngine(repo, MockMailProvider())
    scheduler = Scheduler(
        engine,
        SchedulerConfig(worker_id="worker-test", batch_size=7),
    )

    assert await scheduler.tick(now=datetime.now(UTC)) == 0
    assert repo.worker_id == "worker-test"
    assert repo.batch_size == 7
