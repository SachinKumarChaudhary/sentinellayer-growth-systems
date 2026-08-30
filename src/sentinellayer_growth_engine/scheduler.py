from dataclasses import dataclass
from datetime import datetime

from .engine import SendEngine


@dataclass(frozen=True)
class SchedulerConfig:
    worker_id: str
    batch_size: int = 20


class Scheduler:
    """Thin scheduler; campaign policy remains in the database/engine."""

    def __init__(self, engine: SendEngine, config: SchedulerConfig) -> None:
        if not config.worker_id.strip():
            raise ValueError("worker_id must not be empty")
        if config.batch_size < 1 or config.batch_size > 500:
            raise ValueError("batch_size must be between 1 and 500")
        self.engine = engine
        self.config = config

    async def tick(self, *, now: datetime) -> int:
        return await self.engine.process_due(
            batch_size=self.config.batch_size,
            worker_id=self.config.worker_id,
            now=now,
        )
