import pytest

from sentinellayer_growth_engine.state import (
    SendStatus,
    can_mark_sent,
    can_start_send,
)


def test_only_queued_send_can_start() -> None:
    assert can_start_send(SendStatus.QUEUED) is True
    assert can_start_send(SendStatus.SENT) is False
    assert can_start_send(SendStatus.CANCELLED) is False


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (SendStatus.CLAIMING, True),
        (SendStatus.SENDING, True),
        (SendStatus.QUEUED, False),
        (SendStatus.SENT, False),
        (SendStatus.FAILED, False),
        (SendStatus.CANCELLED, False),
    ],
)
def test_send_can_be_marked_sent_only_in_flight(status: SendStatus, expected: bool) -> None:
    assert can_mark_sent(status) is expected
