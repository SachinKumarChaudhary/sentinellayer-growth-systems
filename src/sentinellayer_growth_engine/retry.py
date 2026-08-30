from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: int = 60
    max_delay_seconds: int = 3600

    def next_attempt_at(self, *, attempt: int, now: datetime | None = None) -> datetime | None:
        if attempt >= self.max_attempts:
            return None
        current = now or datetime.now(timezone.utc)
        delay = min(self.base_delay_seconds * (2 ** max(attempt - 1, 0)), self.max_delay_seconds)
        return current + timedelta(seconds=delay)
