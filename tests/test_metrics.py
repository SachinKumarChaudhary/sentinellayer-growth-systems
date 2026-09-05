import logging

import pytest

from sentinellayer_growth_engine.metrics import OperationalMetrics, emit_event


def test_metrics_snapshot_is_deterministic():
    metrics = OperationalMetrics()
    metrics.increment("mail.sent")
    metrics.increment("mail.sent", 2)
    metrics.set_gauge("queue.depth", 4)

    assert metrics.snapshot() == {
        "counters": {"mail.sent": 3},
        "gauges": {"queue.depth": 4.0},
    }


def test_counter_rejects_negative_increment():
    with pytest.raises(ValueError, match="non-negative"):
        OperationalMetrics().increment("mail.failed", -1)


def test_emit_event_is_json_structured(caplog):
    with caplog.at_level(logging.INFO, logger="sentinellayer.operations"):
        emit_event("mail.failure", provider="staging")

    assert '"event": "mail.failure"' in caplog.text
    assert '"provider": "staging"' in caplog.text
