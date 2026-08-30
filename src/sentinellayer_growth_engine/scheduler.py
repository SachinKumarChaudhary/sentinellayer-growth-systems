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
        self.engine = engine
        self.config = config

    async def tick(self, *, now: datetime) -> int:
        return await self.engine.process_due(
            batch_size=self.config.batch_size,
            now=now,
        )
