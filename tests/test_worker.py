from __future__ import annotations

import asyncio

import pytest

from sentinellayer_growth_engine.worker import MailWorker


class FakeEngine:
    def __init__(self, results: list[int] | None = None, error: Exception | None = None) -> None:
        self.results = results or [0]
        self.error = error
        self.calls = 0

    async def process_due(self, *, batch_size: int, worker_id: str | None, now: object) -> int:
        self.calls += 1
        if self.error:
            raise self.error
        return self.results[min(self.calls - 1, len(self.results) - 1)]


@pytest.mark.asyncio
async def test_run_once_delegates_to_engine() -> None:
    engine = FakeEngine([3])
    worker = MailWorker(engine, batch_size=7, worker_id="worker-a")
    assert await worker.run_once() == 3
    assert engine.calls == 1


@pytest.mark.asyncio
async def test_run_survives_iteration_exception() -> None:
    engine = FakeEngine(error=RuntimeError("boom"))
    worker = MailWorker(engine, tick_seconds=1)
    stop = asyncio.Event()

    async def stop_soon() -> None:
        await asyncio.sleep(0.01)
        stop.set()

    await asyncio.gather(worker.run(stop), stop_soon())
    assert engine.calls >= 1


@pytest.mark.parametrize(("tick_seconds", "batch_size"), [(0, 1), (1, 0)])
def test_worker_rejects_invalid_configuration(tick_seconds: int, batch_size: int) -> None:
    with pytest.raises(ValueError):
        MailWorker(FakeEngine(), tick_seconds=tick_seconds, batch_size=batch_size)
