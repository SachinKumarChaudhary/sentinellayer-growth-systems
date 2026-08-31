from datetime import UTC, datetime

from sentinellayer_growth_engine.engine import DueSend, SendEngine
from sentinellayer_growth_engine.providers import DeliveryStatus, MailProviderAmbiguousError, MockMailProvider


class FakeRepository:
    def __init__(self) -> None:
        self.sent: list[str] = []
        self.failed: list[tuple[str, bool]] = []
        self.ambiguous: list[str] = []
        self.resolved: list[tuple[str, bool]] = []

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

    def mark_ambiguous(self, *, send_id: str, error: str) -> None:
        self.ambiguous.append(send_id)

    def resolve_uncertain(self, *, send_id: str, accepted: bool, provider_message_id: str | None = None, error: str | None = None) -> None:
        self.resolved.append((send_id, accepted))

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


async def test_engine_quarantines_ambiguous_provider_result() -> None:
    class AmbiguousProvider:
        async def send(self, message: object):
            raise MailProviderAmbiguousError("timeout after submission")

        async def health_check(self) -> bool:
            return False

    repo = FakeRepository()
    engine = SendEngine(repo, AmbiguousProvider())
    count = await engine.process_due(worker_id="worker-1", now=datetime.now(UTC))

    assert count == 1
    assert repo.sent == []
    assert repo.failed == []
    assert repo.ambiguous == ["send-1"]


class FakeReconciliationProvider:
    def __init__(self, status: str) -> None:
        self.status = status
        self.lookups: list[str] = []

    async def lookup_delivery(self, message_id: str) -> str:
        self.lookups.append(message_id)
        return self.status


async def test_engine_reconciles_uncertain_as_accepted() -> None:
    repo = FakeRepository()
    provider = FakeReconciliationProvider(DeliveryStatus.ACCEPTED)
    engine = SendEngine(repo, MockMailProvider())
    status = await engine.reconcile_uncertain(
        send_id="send-1",
        message_id="<send-1@sentinellayer.invalid>",
        provider=provider,
    )
    assert status == DeliveryStatus.ACCEPTED
    assert repo.resolved == [("send-1", True)]
    assert provider.lookups == ["<send-1@sentinellayer.invalid>"]


async def test_engine_reconciles_uncertain_as_rejected() -> None:
    repo = FakeRepository()
    provider = FakeReconciliationProvider(DeliveryStatus.REJECTED)
    engine = SendEngine(repo, MockMailProvider())
    status = await engine.reconcile_uncertain(
        send_id="send-1",
        message_id="<send-1@sentinellayer.invalid>",
        provider=provider,
    )
    assert status == DeliveryStatus.REJECTED
    assert repo.resolved == [("send-1", False)]


async def test_engine_keeps_unknown_uncertain() -> None:
    repo = FakeRepository()
    provider = FakeReconciliationProvider(DeliveryStatus.UNKNOWN)
    engine = SendEngine(repo, MockMailProvider())
    status = await engine.reconcile_uncertain(
        send_id="send-1",
        message_id="<send-1@sentinellayer.invalid>",
        provider=provider,
    )
    assert status == DeliveryStatus.UNKNOWN
    assert repo.resolved == []
