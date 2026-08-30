from datetime import UTC, datetime

from sentinellayer_growth_engine.engine import DueSend, SendEngine
from sentinellayer_growth_engine.providers import MockMailProvider


class FakeRepository:
    def __init__(self) -> None:
        self.sent: list[str] = []
        self.failed: list[tuple[str, bool]] = []

    def claim_due(
        self, *, batch_size: int = 20, worker_id: str = "worker"
    ) -> list[DueSend]:
        assert batch_size > 0
        assert worker_id
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

    def mark_sent(
        self, *, send_id: str, message_id: str, provider_message_id: str | None
    ) -> None:
        self.sent.append(send_id)

    def mark_failed(
        self,
        *,
        send_id: str,
        error: str,
        retry_at: datetime | None,
        transient: bool = False,
        provider_code: str | None = None,
    ) -> None:
        self.failed.append((send_id, transient))


async def test_engine_marks_accepted_send_sent() -> None:
    repo = FakeRepository()
    engine = SendEngine(repo, MockMailProvider())

    count = await engine.process_due(worker_id="worker-1", now=datetime.now(UTC))

    assert count == 1
    assert repo.sent == ["send-1"]
    assert repo.failed == []


async def test_engine_marks_permanent_provider_rejection_failed() -> None:
    repo = FakeRepository()
    engine = SendEngine(repo, MockMailProvider(accept=False))

    count = await engine.process_due(worker_id="worker-1", now=datetime.now(UTC))

    assert count == 1
    assert repo.sent == []
    assert repo.failed == [("send-1", False)]


async def test_engine_marks_transient_provider_rejection_retryable() -> None:
    repo = FakeRepository()
    provider = MockMailProvider(
        accept=False, transient=True, provider_code="421"
    )
    engine = SendEngine(repo, provider)

    count = await engine.process_due(worker_id="worker-1", now=datetime.now(UTC))

    assert count == 1
    assert repo.sent == []
    assert repo.failed == [("send-1", True)]
