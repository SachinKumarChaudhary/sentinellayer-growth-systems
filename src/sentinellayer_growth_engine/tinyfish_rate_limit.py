from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass


class TinyFishQuotaExceeded(RuntimeError):
    """Raised when a local safety budget cannot admit another request."""


@dataclass(frozen=True)
class TinyFishRateLimitPolicy:
    search_per_minute: int = 27
    search_per_hour: int = 450
    fetch_urls_per_minute: int = 135
    fetch_urls_per_day: int = 900

    def __post_init__(self) -> None:
        if min(
            self.search_per_minute,
            self.search_per_hour,
            self.fetch_urls_per_minute,
            self.fetch_urls_per_day,
        ) <= 0:
            raise ValueError("TinyFish rate limits must be positive")
        if self.search_per_minute * 60 > self.search_per_hour:
            raise ValueError("search_per_minute exceeds hourly search budget")


class TinyFishRateLimiter:
    """Process-local limiter with conservative headroom below TinyFish limits."""

    def __init__(
        self,
        policy: TinyFishRateLimitPolicy | None = None,
        *,
        clock: callable = time.monotonic,
        wall_clock: callable = time.time,
    ) -> None:
        self.policy = policy or TinyFishRateLimitPolicy()
        self._clock = clock
        self._wall_clock = wall_clock
        self._search_minute: deque[float] = deque()
        self._search_hour: deque[float] = deque()
        self._fetch_minute: deque[tuple[float, int]] = deque()
        self._fetch_day: deque[tuple[float, int]] = deque()

    def acquire_search(self) -> None:
        self._acquire_search_window()
        now = self._clock()
        self._search_minute.append(now)
        self._search_hour.append(now)

    def acquire_fetch(self, url_count: int) -> None:
        if not 1 <= url_count <= 10:
            raise ValueError("TinyFish Fetch url_count must be between 1 and 10")
        self._prune()
        now = self._clock()
        today = self._wall_clock()
        minute_total = sum(count for _, count in self._fetch_minute)
        day_total = sum(count for _, count in self._fetch_day)
        if minute_total + url_count > self.policy.fetch_urls_per_minute:
            wait = self._wait_for_fetch_minute(url_count)
            raise TinyFishQuotaExceeded(
                f"TinyFish Fetch minute budget exhausted; retry in {wait:.1f}s"
            )
        if day_total + url_count > self.policy.fetch_urls_per_day:
            raise TinyFishQuotaExceeded("TinyFish Fetch daily safety budget exhausted")
        self._fetch_minute.append((now, url_count))
        self._fetch_day.append((today, url_count))

    def _acquire_search_window(self) -> None:
        self._prune()
        now = self._clock()
        if len(self._search_minute) >= self.policy.search_per_minute:
            wait = max(0.0, 60.0 - (now - self._search_minute[0]))
            raise TinyFishQuotaExceeded(
                f"TinyFish Search minute budget exhausted; retry in {wait:.1f}s"
            )
        if len(self._search_hour) >= self.policy.search_per_hour:
            wait = max(0.0, 3600.0 - (now - self._search_hour[0]))
            raise TinyFishQuotaExceeded(
                f"TinyFish Search hourly safety budget exhausted; retry in {wait / 60:.1f}m"
            )

    def _wait_for_fetch_minute(self, url_count: int) -> float:
        running = sum(count for _, count in self._fetch_minute)
        for timestamp, count in self._fetch_minute:
            running -= count
            if running + url_count <= self.policy.fetch_urls_per_minute:
                return max(0.0, 60.0 - (self._clock() - timestamp))
        return 60.0

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
