from datetime import datetime, timezone

from sentinellayer_growth_engine.engine import DueSend, SendEngine
from sentinellayer_growth_engine.providers import MockMailProvider


class FakeRepository:
    def __init__(self) -> None:
        self.sent: list[str] = []
        self.failed: list[str] = []

    async def claim_due(self, *, worker_id: str, now: datetime) -> list[DueSend]:
        return [
            DueSend(
                send_id="send-1",
                sender="sender@sentinellayer.invalid",
                recipient="recipient@example.invalid",
                subject="Test",
                body_text="Hello",
                message_id="<send-1@sentinellayer.invalid>",
            )
        ]

    async def mark_sent(self, *, send_id: str, message_id: str, provider_message_id: str | None) -> None:
        self.sent.append(send_id)

    async def mark_failed(self, *, send_id: str, error: str) -> None:
        self.failed.append(send_id)


async def test_engine_marks_accepted_send_sent() -> None:
    repo = FakeRepository()
    engine = SendEngine(repo, MockMailProvider())

    count = await engine.process_due(worker_id="worker-1", now=datetime.now(timezone.utc))

    assert count == 1
    assert repo.sent == ["send-1"]
    assert repo.failed == []


async def test_engine_marks_provider_rejection_failed() -> None:
    repo = FakeRepository()
    engine = SendEngine(repo, MockMailProvider(accept=False))

    count = await engine.process_due(worker_id="worker-1", now=datetime.now(timezone.utc))

    assert count == 1
    assert repo.sent == []
    assert repo.failed == ["send-1"]
