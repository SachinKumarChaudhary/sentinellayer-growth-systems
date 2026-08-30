from dataclasses import dataclass

from sentinellayer_growth_engine.db import ClaimedSend
from sentinellayer_growth_engine.providers import MockMailProvider, OutboundMessage
from sentinellayer_growth_engine.service import SendService


@dataclass
class FakeRenderer:
    def render(self, send: ClaimedSend) -> OutboundMessage:
        return OutboundMessage(
            message_id=f"<{send.send_id}@sentinellayer.invalid>",
            sender="sender@sentinellayer.invalid",
            recipient="recipient@example.invalid",
            subject="Test",
            body_text="Test body",
            headers={"X-SL-Send-Id": send.send_id},
        )


class FakeDb:
    pass


async def test_send_service_processes_claimed_send() -> None:
    provider = MockMailProvider()
    service = SendService(FakeDb(), provider, FakeRenderer())  # type: ignore[arg-type]
    claimed = ClaimedSend(
        send_id="send-1",
        person_id=1,
        campaign_id="campaign-1",
        sequence_step_id="step-1",
        mailbox_id="mailbox-1",
        scheduled_at="2026-08-30T12:00:00Z",
    )

    result = await service.process_claimed(claimed)

    assert result.accepted is True
    assert result.send_id == "send-1"
    assert provider.sent[0].headers["X-SL-Send-Id"] == "send-1"
