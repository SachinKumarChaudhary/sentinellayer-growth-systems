from __future__ import annotations

import json
import logging
import threading
from collections import Counter
from typing import Any


class OperationalMetrics:
    """Small dependency-free metrics registry for runtime signals.

    Metrics are process-local by design. They provide deterministic counters and
    gauges for logs, health endpoints, and future Prometheus/OpenTelemetry
    adapters without coupling core runtime code to an external metrics service.
    """

    def __init__(self) -> None:
        self._counters: Counter[str] = Counter()
        self._gauges: dict[str, float] = {}
        self._lock = threading.Lock()

    def increment(self, name: str, value: int = 1) -> None:
        if value < 0:
            raise ValueError("counter increments must be non-negative")
        with self._lock:
            self._counters[name] += value

    def set_gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = float(value)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "counters": dict(sorted(self._counters.items())),
                "gauges": dict(sorted(self._gauges.items())),
            }


logger = logging.getLogger("sentinellayer.operations")


def emit_event(event: str, **fields: Any) -> None:
    """Emit one structured operational event without secret-bearing fields."""
    payload = {"event": event, **fields}
    logger.info(json.dumps(payload, default=str, sort_keys=True))
