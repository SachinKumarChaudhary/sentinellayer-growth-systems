from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol

from .conversation import ConversationProcessor
from .conversation_sales import ConversationSalesBridge


class ConversationStore(Protocol):
    def persist_handoff(
        self,
        *,
        handoff: dict[str, Any],
        sender_email: str,
        subject: str,
        body_text: str,
        provider_message_id: str,
        thread_key: str,
        received_at: datetime,
    ) -> dict[str, Any]:
        ...

    def cancel_future_sends_for_person(self, *, person_id: int, reason: str) -> None:
        ...

    def add_suppression(self, *, email: str, reason: str) -> None:
        ...


class ConversationRuntime:
    """Persist inbound replies, enforce deterministic stop rules, and trigger Sales."""

    def __init__(
        self,
        store: ConversationStore,
        *,
        processor: ConversationProcessor | None = None,
        sales_bridge: ConversationSalesBridge | None = None,
    ) -> None:
        self.store = store
        self.processor = processor or ConversationProcessor()
        self.sales_bridge = sales_bridge

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
        received_at: datetime | None = None,
        sales_priority: str = "P2",
    ) -> dict[str, Any]:
        handoff = self.processor.process(
            account_id=account_id,
            person_id=person_id,
            sender_email=sender_email,
            subject=subject,
            body_text=body_text,
            provider_message_id=provider_message_id,
            thread_key=thread_key,
            source_send_id=source_send_id,
            received_at=received_at,
        )
        persisted = self.store.persist_handoff(
            handoff=handoff,
            sender_email=sender_email,
            subject=subject,
            body_text=body_text,
            provider_message_id=provider_message_id,
            thread_key=thread_key,
            received_at=received_at or datetime.now(UTC),
        )

        classification = handoff["classification"]
        if classification in {"unsubscribe", "negative"}:
            try:
                numeric_person_id = int(person_id)
            except ValueError:
                numeric_person_id = 0
            if numeric_person_id > 0:
                self.store.cancel_future_sends_for_person(
                    person_id=numeric_person_id,
                    reason=handoff["recommended_action"],
                )
            if classification == "unsubscribe":
                self.store.add_suppression(
                    email=sender_email,
                    reason="inbound_unsubscribe",
                )

        sales = None
        if self.sales_bridge is not None and classification in {"interested", "question"}:
            sales = self.sales_bridge.bridge(handoff, priority=sales_priority)

        return {
            "handoff": handoff,
            "persisted": persisted,
            "sales": sales,
            "stop_sequence": classification in {"unsubscribe", "negative"},
        }

