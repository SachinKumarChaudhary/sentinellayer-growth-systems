from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from .contracts import ContractValidationError, validate_contract

UNSUBSCRIBE_PATTERNS = (r"\bunsubscribe\b", r"\bremove me\b", r"\bstop emailing\b", r"\bstop contacting\b")
NEGATIVE_PATTERNS = (r"\bnot interested\b", r"\bno thanks\b", r"\bno thank you\b")
NOT_NOW_PATTERNS = (r"\bnot now\b", r"\bmaybe later\b", r"\breach out .* later\b")
OOO_PATTERNS = (r"\bout of office\b", r"\baway from .*office\b", r"\bback on\b")
QUESTION_PATTERNS = (r"\?$", r"\bwhat(?:'s| is)\b", r"\bhow does\b", r"\bcan you\b")
INTEREST_PATTERNS = (
    r"\binterested\b", r"\btell me more\b", r"\blet's talk\b",
    r"\bschedule\b", r"\bbook .*call\b", r"\bworth a chat\b",
)

def _matches(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE | re.MULTILINE) for pattern in patterns)

def classify_reply(subject: str, body_text: str) -> tuple[str, str]:
    text = f"{subject}\n{body_text}".strip()
    if not text:
        return "unclassified", "empty_reply"
    if _matches(UNSUBSCRIBE_PATTERNS, text):
        return "unsubscribe", "explicit_unsubscribe"
    if _matches(NEGATIVE_PATTERNS, text):
        return "negative", "explicit_negative"
    if _matches(OOO_PATTERNS, text):
        return "ooo", "out_of_office_signal"
    if _matches(NOT_NOW_PATTERNS, text):
        return "not_now", "defer_signal"
    if _matches(INTEREST_PATTERNS, text):
        return "interested", "positive_interest_signal"
    if _matches(QUESTION_PATTERNS, text):
        return "question", "question_signal"
    return "other", "no_known_classification_signal"

def recommended_action(classification: str) -> str:
    return {
        "interested": "human_follow_up",
        "question": "human_follow_up",
        "not_now": "schedule_later",
        "negative": "stop_cold_sequence",
        "unsubscribe": "suppress_contact",
        "ooo": "defer_until_return",
        "other": "human_review",
        "unclassified": "human_review",
    }.get(classification, "human_review")

class ConversationProcessor:
    """Normalize and classify an inbound reply without performing side effects."""

    def process(
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
        reply_id: UUID | None = None,
        conversation_id: UUID | None = None,
        received_at: datetime | None = None,
    ) -> dict[str, Any]:
        if not account_id.strip() or not person_id.strip():
            raise ContractValidationError("account_id and person_id are required")
        if not sender_email.strip() or "@" not in sender_email:
            raise ContractValidationError("valid sender_email is required")
        if not provider_message_id.strip() or not thread_key.strip():
            raise ContractValidationError("provider_message_id and thread_key are required")
        received_at = received_at or datetime.now(UTC)
        if received_at.tzinfo is None:
            raise ContractValidationError("received_at must be timezone-aware")
        source_id: UUID | None = None
        if source_send_id is not None:
            try:
                source_id = UUID(source_send_id)
            except (ValueError, AttributeError, TypeError) as exc:
                raise ContractValidationError("source_send_id must be a UUID") from exc

        rid = reply_id or uuid4()
        cid = conversation_id or uuid4()
        classification, reason = classify_reply(subject, body_text)
        payload = {
            "schema_version": "1.0",
            "conversation_id": str(cid),
            "reply_id": str(rid),
            "account_id": account_id,
            "person_id": person_id,
            "classification": classification,
            "conversation_state": "action_selected",
            "source_send_id": str(source_id) if source_id else None,
            "recommended_action": recommended_action(classification),
            "intent_snapshot": None,
            "timeline": [{
                "provider_message_id": provider_message_id,
                "thread_key": thread_key,
                "received_at": received_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            }],
            "commitments": [],
            "objections": [],
            "questions": [body_text.strip()] if classification == "question" else [],
            "evidence": [{"signal": reason}],
            "created_at": received_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        }
        return validate_contract("conversation_handoff", payload)
