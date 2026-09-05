from __future__ import annotations

from dataclasses import dataclass
from email.utils import parseaddr
from typing import Any

from .conversation import ConversationProcessor


class InboundNormalizationError(ValueError):
    """Raised when an inbound provider message cannot be normalized safely."""


@dataclass(frozen=True)
class InboundMessage:
    provider_message_id: str
    sender_email: str
    subject: str
    body_text: str
    thread_key: str
    account_id: str
    person_id: str
    source_send_id: str | None = None


class InboundReplyAdapter:
    """Normalize a provider-neutral inbound message and hand it to Conversation."""

    def __init__(self, processor: ConversationProcessor | None = None) -> None:
        self.processor = processor or ConversationProcessor()

    @staticmethod
    def normalize(raw: dict[str, Any]) -> InboundMessage:
        provider_message_id = str(raw.get("provider_message_id") or "").strip()
        sender = str(raw.get("sender") or raw.get("from") or "").strip()
        sender_email = parseaddr(sender)[1]
        subject = str(raw.get("subject") or "")
        body_text = str(raw.get("body_text") or raw.get("text") or "")
        thread_key = str(raw.get("thread_key") or raw.get("in_reply_to") or "").strip()
        account_id = str(raw.get("account_id") or "").strip()
        person_id = str(raw.get("person_id") or "").strip()
        source_send_id = raw.get("source_send_id")
        if not provider_message_id:
            raise InboundNormalizationError("provider_message_id is required")
        if not sender_email or "@" not in sender_email:
            raise InboundNormalizationError("valid sender email is required")
        if not thread_key:
            raise InboundNormalizationError("thread key is required")
        if not account_id or not person_id:
            raise InboundNormalizationError("account_id and person_id are required")
        return InboundMessage(
            provider_message_id=provider_message_id,
            sender_email=sender_email,
            subject=subject,
            body_text=body_text,
            thread_key=thread_key,
            account_id=account_id,
            person_id=person_id,
            source_send_id=str(source_send_id) if source_send_id is not None else None,
        )

    def process(self, raw: dict[str, Any]) -> dict[str, Any]:
        message = self.normalize(raw)
        return self.processor.process(
            account_id=message.account_id,
            person_id=message.person_id,
            sender_email=message.sender_email,
            subject=message.subject,
            body_text=message.body_text,
            provider_message_id=message.provider_message_id,
            thread_key=message.thread_key,
            source_send_id=message.source_send_id,
        )
