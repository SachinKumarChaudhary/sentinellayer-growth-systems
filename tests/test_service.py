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
