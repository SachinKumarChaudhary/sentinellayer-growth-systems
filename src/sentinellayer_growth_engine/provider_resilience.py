from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class CacheEntry(Generic[T]):
    value: T
    expires_at: float


class TTLCache(Generic[T]):
    """Small bounded process-local cache with deterministic TTL behavior."""

    def __init__(
        self,
        *,
        max_entries: int = 1024,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        self._max_entries = max_entries
        self._clock = clock
        self._entries: OrderedDict[str, CacheEntry[T]] = OrderedDict()

    def get(self, key: str) -> T | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= self._clock():
            del self._entries[key]
            return None
        self._entries.move_to_end(key)
        return entry.value

    def set(self, key: str, value: T, *, ttl_seconds: float) -> None:
        if ttl_seconds <= 0:
            return
        while len(self._entries) >= self._max_entries:
            self._entries.popitem(last=False)
        self._entries[key] = CacheEntry(
            value=value,
            expires_at=self._clock() + ttl_seconds,
        )

    def clear(self) -> None:
        self._entries.clear()


def request_fingerprint(*, method: str, url: str, body: dict[str, Any] | None) -> str:
    payload = {
        "body": body,
        "method": method.upper(),
        "url": url,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class TinyFishRequestTelemetry:
    operation: str
    request_fingerprint: str
    started_at: datetime
    finished_at: datetime
    latency_ms: int
    quota_units: int
    attempts: int
    retry_count: int
    cache_hit: bool
    status: str
    http_status: int | None = None
    failure_code: str | None = None


TelemetrySink = Callable[[TinyFishRequestTelemetry], None]


def utc_now() -> datetime:
    return datetime.now(UTC)
