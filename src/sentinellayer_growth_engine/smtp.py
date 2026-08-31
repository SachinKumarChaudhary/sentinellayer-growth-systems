from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

from .providers import MailProviderAmbiguousError, MailProviderError, OutboundMessage, SendResult
class SmtpMailProvider:
    """SMTP submission provider for authenticated port 587/465 delivery.

    A timeout after DATA is treated as ambiguous: SMTP cannot prove whether the
    recipient server accepted the message, so callers must not blindly retry it.
    """

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        timeout_seconds: float = 30.0,
        use_ssl: bool | None = None,
    ) -> None:
        if port not in (465, 587):
            raise ValueError("SMTP submission must use port 465 or 587")
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout_seconds = timeout_seconds
        self.use_ssl = port == 465 if use_ssl is None else use_ssl

    async def send(self, message: OutboundMessage) -> SendResult:
        return await asyncio.to_thread(self._send_sync, message)

    def _send_sync(self, message: OutboundMessage) -> SendResult:
        mail = EmailMessage()
        mail["From"] = message.sender
        mail["To"] = message.recipient
        mail["Subject"] = message.subject
        mail["Message-ID"] = message.message_id
        for name, value in message.headers.items():
            if name.lower() != "message-id":
                mail[name] = value
        mail.set_content(message.body_text)

        smtp: smtplib.SMTP | smtplib.SMTP_SSL | None = None
        try:
            if self.use_ssl:
                smtp = smtplib.SMTP_SSL(
                    self.host, self.port, timeout=self.timeout_seconds
                )
            else:
                smtp = smtplib.SMTP(
                    self.host, self.port, timeout=self.timeout_seconds
                )
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()

            smtp.login(self.username, self.password)
            refused = smtp.send_message(mail)
            if refused:
                details = "; ".join(
                    f"{recipient}: {response}" for recipient, response in refused.items()
                )
                transient = any(
                    isinstance(response, tuple)
                    and len(response) >= 1
                    and 400 <= int(response[0]) < 500
                    for response in refused.values()
                )
                code = next(
                    (
                        str(response[0])
                        for response in refused.values()
                        if isinstance(response, tuple) and len(response) >= 1
                    ),
                    None,
                )
                return SendResult(
                    accepted=False,
                    error=f"SMTP refused recipient(s): {details}",
                    transient=transient,
                    provider_code=code,
                )
            return SendResult(
                accepted=True,
                provider_message_id=message.message_id,
            )
        except (TimeoutError, smtplib.SMTPServerDisconnected) as exc:
            raise MailProviderAmbiguousError(
                "SMTP connection ended during/after submission; delivery status is unknown"
            ) from exc
        except smtplib.SMTPResponseException as exc:
            transient = 400 <= exc.smtp_code < 500
            return SendResult(
                accepted=False,
                error=exc.smtp_error.decode(errors="replace")
                if isinstance(exc.smtp_error, bytes)
                else str(exc.smtp_error),
                transient=transient,
                provider_code=str(exc.smtp_code),
            )
        except smtplib.SMTPException as exc:
            raise MailProviderError(f"SMTP provider error: {exc}") from exc
        finally:
            if smtp is not None:
                try:
                    smtp.quit()
                except (OSError, smtplib.SMTPException):
                    smtp.close()

    async def health_check(self) -> bool:
        return await asyncio.to_thread(self._health_check_sync)

    def _health_check_sync(self) -> bool:
        smtp: smtplib.SMTP | smtplib.SMTP_SSL | None = None
        try:
            if self.use_ssl:
                smtp = smtplib.SMTP_SSL(
                    self.host, self.port, timeout=self.timeout_seconds
                )
            else:
                smtp = smtplib.SMTP(self.host, self.port, timeout=self.timeout_seconds)
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
            smtp.login(self.username, self.password)
            return True
        except (OSError, smtplib.SMTPException, TimeoutError):
            return False
        finally:
            if smtp is not None:
                try:
                    smtp.quit()
                except (OSError, smtplib.SMTPException):
                    smtp.close()
