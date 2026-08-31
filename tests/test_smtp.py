import smtplib

import pytest

from sentinellayer_growth_engine.providers import OutboundMessage, SendResult
from sentinellayer_growth_engine.smtp import MailProviderAmbiguousError, SmtpMailProvider


def message() -> OutboundMessage:
    return OutboundMessage(
        message_id="<ci-smtp-1@sentinellayer.invalid>",
        sender="sender@sentinellayer.invalid",
        recipient="recipient@example.invalid",
        subject="CI SMTP",
        body_text="test",
        headers={"X-SL-Send-Id": "send-1"},
    )


def test_smtp_provider_requires_submission_port() -> None:
    with pytest.raises(ValueError):
        SmtpMailProvider(
            host="smtp.example.invalid",
            port=25,
            username="u",
            password="p",
        )


@pytest.mark.asyncio
async def test_smtp_transient_4xx_is_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSMTP:
        def __init__(self, *args: object, **kwargs: object) -> None: pass
        def ehlo(self) -> None: pass
        def starttls(self) -> None: pass
        def login(self, u: str, p: str) -> None: pass
        def send_message(self, m: object) -> None:
            raise smtplib.SMTPResponseException(421, b"temporary")
        def quit(self) -> None: pass
        def close(self) -> None: pass

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    provider = SmtpMailProvider(
        host="smtp.example.invalid", port=587, username="u", password="p"
    )
    result = await provider.send(message())
    assert result.accepted is False
    assert result.transient is True
    assert result.provider_code == "421"


@pytest.mark.asyncio
async def test_smtp_timeout_is_ambiguous(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSMTP:
        def __init__(self, *args: object, **kwargs: object) -> None: pass
        def ehlo(self) -> None: pass
        def starttls(self) -> None: pass
        def login(self, u: str, p: str) -> None: pass
        def send_message(self, m: object) -> None:
            raise TimeoutError("timed out after DATA")
        def quit(self) -> None: pass
        def close(self) -> None: pass

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    provider = SmtpMailProvider(
        host="smtp.example.invalid", port=587, username="u", password="p"
    )
    with pytest.raises(MailProviderAmbiguousError):
        await provider.send(message())


@pytest.mark.asyncio
async def test_smtp_refused_recipient_is_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSMTP:
        def __init__(self, *args: object, **kwargs: object) -> None: pass
        def ehlo(self) -> None: pass
        def starttls(self) -> None: pass
        def login(self, u: str, p: str) -> None: pass
        def send_message(self, m: object) -> dict[str, tuple[int, bytes]]:
            return {"recipient@example.invalid": (550, b"mailbox unavailable")}
        def quit(self) -> None: pass
        def close(self) -> None: pass

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    provider = SmtpMailProvider(
        host="smtp.example.invalid", port=587, username="u", password="p"
    )
    result = await provider.send(message())
    assert result.accepted is False
    assert result.transient is False
    assert result.provider_code == "550"


@pytest.mark.asyncio
async def test_smtp_refused_recipient_4xx_is_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeSMTP:
        def __init__(self, *args: object, **kwargs: object) -> None: pass
        def ehlo(self) -> None: pass
        def starttls(self) -> None: pass
        def login(self, u: str, p: str) -> None: pass
        def send_message(self, m: object) -> dict[str, tuple[int, bytes]]:
            return {"recipient@example.invalid": (451, b"try later")}
        def quit(self) -> None: pass
        def close(self) -> None: pass

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    provider = SmtpMailProvider(
        host="smtp.example.invalid", port=587, username="u", password="p"
    )
    result = await provider.send(message())
    assert result.accepted is False
    assert result.transient is True
    assert result.provider_code == "451"
