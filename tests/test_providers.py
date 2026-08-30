from sentinellayer_growth_engine.providers import MockMailProvider, OutboundMessage


async def test_mock_provider_accepts_message() -> None:
    provider = MockMailProvider()
    message = OutboundMessage(
        message_id="<test-1@sentinellayer.invalid>",
        sender="sender@sentinellayer.invalid",
        recipient="recipient@example.invalid",
        subject="Test",
        body_text="Test body",
        headers={},
    )
    result = await provider.send(message)
    assert result.accepted is True
    assert len(provider.sent) == 1


async def test_mock_provider_can_fail() -> None:
    provider = MockMailProvider(accept=False)
    message = OutboundMessage(
        message_id="<test-2@sentinellayer.invalid>",
        sender="sender@sentinellayer.invalid",
        recipient="recipient@example.invalid",
        subject="Test",
        body_text="Test body",
        headers={},
    )
    result = await provider.send(message)
    assert result.accepted is False
    assert provider.sent == []
