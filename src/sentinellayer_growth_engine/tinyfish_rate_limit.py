from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from collections.abc import Callable


class TinyFishQuotaExceeded(RuntimeError):
    """Raised when a daily TinyFish safety budget is exhausted."""


@dataclass(frozen=True)
class TinyFishRateLimitPolicy:
    search_per_minute: int = 27
    search_per_hour: int = 450
    fetch_urls_per_minute: int = 135
    fetch_urls_per_day: int = 900
    max_retry_attempts: int = 4

    def __post_init__(self) -> None:
        if min(
            self.search_per_minute,
            self.search_per_hour,
            self.fetch_urls_per_minute,
            self.fetch_urls_per_day,
            self.max_retry_attempts,
        ) <= 0:
            raise ValueError("TinyFish rate limits must be positive")


class TinyFishRateLimiter:
    """Process-local limiter with conservative headroom below TinyFish limits."""

    def __init__(
        self,
        policy: TinyFishRateLimitPolicy | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.policy = policy or TinyFishRateLimitPolicy()
        self._clock = clock
        self._wall_clock = wall_clock
        self._sleep = sleep
        self._search_minute: deque[float] = deque()
        self._search_hour: deque[float] = deque()
        self._fetch_minute: deque[tuple[float, int]] = deque()
        self._fetch_day: deque[tuple[float, int]] = deque()

    def acquire_search(self) -> None:
        while True:
            self._prune()
            now = self._clock()
            waits: list[float] = []
            if len(self._search_minute) >= self.policy.search_per_minute:
                waits.append(max(0.01, 60.0 - (now - self._search_minute[0])))
            if len(self._search_hour) >= self.policy.search_per_hour:
                waits.append(max(0.01, 3600.0 - (now - self._search_hour[0])))
            if not waits:
                self._search_minute.append(now)
                self._search_hour.append(now)
                return
            self._sleep(min(waits))

    def acquire_fetch(self, url_count: int) -> None:
        if not 1 <= url_count <= 10:
            raise ValueError("TinyFish Fetch url_count must be between 1 and 10")
        while True:
            self._prune()
            now = self._clock()
            wall_now = self._wall_clock()
            minute_total = sum(count for _, count in self._fetch_minute)
            day_total = sum(count for _, count in self._fetch_day)
            if day_total + url_count > self.policy.fetch_urls_per_day:
                raise TinyFishQuotaExceeded("TinyFish Fetch daily safety budget exhausted")
            if minute_total + url_count <= self.policy.fetch_urls_per_minute:
                self._fetch_minute.append((now, url_count))
                self._fetch_day.append((wall_now, url_count))
                return
            wait = max(0.01, 60.0 - (now - self._fetch_minute[0][0]))
            self._sleep(wait)

    def _prune(self) -> None:
        now = self._clock()
        wall_now = self._wall_clock()
        while self._search_minute and now - self._search_minute[0] >= 60:
            self._search_minute.popleft()
        while self._search_hour and now - self._search_hour[0] >= 3600:
            self._search_hour.popleft()
        while self._fetch_minute and now - self._fetch_minute[0][0] >= 60:
            self._fetch_minute.popleft()
        while self._fetch_day and wall_now - self._fetch_day[0][0] >= 86400:
            self._fetch_day.popleft()
