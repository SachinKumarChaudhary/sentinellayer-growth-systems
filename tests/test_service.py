from dataclasses import dataclass

from sentinellayer_growth_engine.engine import DueSend
from sentinellayer_growth_engine.providers import MockMailProvider, OutboundMessage
from sentinellayer_growth_engine.service import SendService


@dataclass
class FakeRenderer:
    def render(self, send: DueSend) -> OutboundMessage:
        return OutboundMessage(
            message_id=send.message_id,
            sender=send.sender,
            recipient=send.recipient,
            subject=send.subject,
            body_text=send.body_text,
            headers={"X-SL-Send-Id": send.send_id},
        )


async def test_send_service_processes_claimed_send() -> None:
    provider = MockMailProvider()
    service = SendService(provider, FakeRenderer())
    claimed = DueSend(
        send_id="send-1",
        sender="sender@sentinellayer.invalid",
        recipient="recipient@example.invalid",
        subject="Test",
        body_text="Test body",
        message_id="<send-1@sentinellayer.invalid>",
        attempt_count=1,
    )

    result = await service.process_claimed(claimed)

    assert result.accepted is True
    assert result.send_id == "send-1"
    assert provider.sent[0].headers["X-SL-Send-Id"] == "send-1"


def test_settings_include_imap_defaults() -> None:
    from sentinellayer_growth_engine.config import Settings
    settings = Settings(database_url="postgresql://example")
    assert settings.imap_port == 993
    assert settings.imap_mailbox == "INBOX"


def test_staging_real_email_fails_closed() -> None:
    from sentinellayer_growth_engine.config import Settings
    settings = Settings(
        database_url="postgresql://example",
        environment="staging",
        real_email_enabled=True,
    )
    try:
        settings.assert_safe()
    except RuntimeError as exc:
        assert "must remain false outside production" in str(exc)
    else:
        raise AssertionError("expected fail-closed staging configuration")
