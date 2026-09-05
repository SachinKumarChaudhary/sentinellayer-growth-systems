from __future__ import annotations

import email
import imaplib
from dataclasses import dataclass
from email.header import decode_header
from email.message import Message
from email.utils import parseaddr
from html.parser import HTMLParser
from typing import Protocol


class InboundIdentityResolver(Protocol):
    def resolve(self, *, sender_email: str, thread_key: str) -> tuple[str, str] | None:
        """Return account_id/person_id for a known inbound correspondent."""
        ...


class InboundHandler(Protocol):
    def handle_inbound(
        self,
        *,
        account_id: str,
        person_id: str,
        sender_email: str,
        subject: str,
        body_text: str,
        provider_message_id: str,
        thread_key: str,
        source_send_id: str | None = None,
    ) -> dict[str, object]:
        ...


@dataclass(frozen=True)
class ImapInboundMessage:
    uid: str
    provider_message_id: str
    sender_email: str
    subject: str
    body_text: str
    thread_key: str
    source_send_id: str | None


class _HTMLText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _decode_header(value: str | None) -> str:
    if not value:
        return ""
    parts: list[str] = []
    for chunk, charset in decode_header(value):
        if isinstance(chunk, bytes):
            parts.append(chunk.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(chunk)
    return "".join(parts)


def _text_from_message(message: Message) -> str:
    if message.is_multipart():
        plain_parts: list[str] = []
        html_parts: list[str] = []
        for part in message.walk():
            if part.is_multipart():
                continue
            disposition = (part.get("Content-Disposition") or "").lower()
            if "attachment" in disposition:
                continue
            content_type = part.get_content_type()
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset() or "utf-8"
            if isinstance(payload, bytes):
                text = payload.decode(charset, errors="replace")
            elif isinstance(payload, str):
                text = payload
            else:
                continue
            if content_type == "text/plain":
                plain_parts.append(text)
            elif content_type == "text/html":
                html_parts.append(text)
        if plain_parts:
            return "\n\n".join(plain_parts).strip()
        if html_parts:
            parser = _HTMLText()
            parser.feed("\n\n".join(html_parts))
            return "\n".join(parser.parts).strip()
        return ""
    payload = message.get_payload(decode=True)
    if isinstance(payload, bytes):
        return payload.decode(message.get_content_charset() or "utf-8", errors="replace").strip()
    if isinstance(payload, str):
        return payload.strip()
    return ""


def parse_message(uid: str, raw_message: bytes) -> ImapInboundMessage:
    msg = email.message_from_bytes(raw_message)
    provider_message_id = _decode_header(msg.get("Message-ID")).strip()
    sender_email = parseaddr(_decode_header(msg.get("From")))[1].strip().lower()
    subject = _decode_header(msg.get("Subject")).strip()
    in_reply_to = _decode_header(msg.get("In-Reply-To")).strip()
    references = _decode_header(msg.get("References")).split()
    thread_key = in_reply_to or (references[0] if references else provider_message_id)
    source_send_id = _decode_header(msg.get("X-SL-Send-Id")).strip() or None
    if not provider_message_id:
        raise ValueError("inbound message missing Message-ID")
    if not sender_email or "@" not in sender_email:
        raise ValueError("inbound message has invalid From address")
    if not thread_key:
        raise ValueError("inbound message has no thread key")
    return ImapInboundMessage(
        uid=uid,
        provider_message_id=provider_message_id,
        sender_email=sender_email,
        subject=subject,
        body_text=_text_from_message(msg),
        thread_key=thread_key,
        source_send_id=source_send_id,
    )


class ImapInboundProvider:
    """Poll an authenticated IMAP mailbox and hand normalized replies to Conversation."""

    def __init__(
        self,
        *,
        host: str,
        username: str,
        password: str,
        port: int = 993,
        mailbox: str = "INBOX",
        timeout_seconds: float = 30.0,
    ) -> None:
        if port != 993:
            raise ValueError("IMAP must use TLS port 993")
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.mailbox = mailbox
        self.timeout_seconds = timeout_seconds

    def poll_once(
        self,
        *,
        resolver: InboundIdentityResolver,
        handler: InboundHandler,
        mark_seen: bool = True,
    ) -> list[dict[str, object]]:
        client = imaplib.IMAP4_SSL(self.host, self.port, timeout=self.timeout_seconds)
        try:
            client.login(self.username, self.password)
            status, _ = client.select(self.mailbox, readonly=not mark_seen)
            if status != "OK":
                raise RuntimeError(f"IMAP select failed for mailbox {self.mailbox!r}")
            status, data = client.uid("SEARCH", "UNSEEN")
            if status != "OK":
                raise RuntimeError("IMAP UNSEEN search failed")
            uids = (data[0] or b"").split()
            results: list[dict[str, object]] = []
            for uid_bytes in uids:
                uid = uid_bytes.decode("ascii", errors="strict")
                status, fetched = client.uid("FETCH", uid, "(RFC822)")
                if status != "OK" or not fetched:
                    continue
                raw = next(
                    (item[1] for item in fetched if isinstance(item, tuple) and len(item) == 2),
                    None,
                )
                if not isinstance(raw, bytes):
                    continue
                message = parse_message(uid, raw)
                identity = resolver.resolve(
                    sender_email=message.sender_email,
                    thread_key=message.thread_key,
                )
                if identity is None:
                    results.append({"uid": uid, "status": "unresolved_identity"})
                    continue
                account_id, person_id = identity
                outcome = handler.handle_inbound(
                    account_id=account_id,
                    person_id=person_id,
                    sender_email=message.sender_email,
                    subject=message.subject,
                    body_text=message.body_text,
                    provider_message_id=message.provider_message_id,
                    thread_key=message.thread_key,
                    source_send_id=message.source_send_id,
                )
                if mark_seen:
                    client.uid("STORE", uid, "+FLAGS", "(\\Seen)")
                results.append(
                    {
                        "uid": uid,
                        "status": "processed",
                        "outcome": outcome,
                    }
                )
            return results
        finally:
            try:
                client.logout()
            except OSError:
                pass
