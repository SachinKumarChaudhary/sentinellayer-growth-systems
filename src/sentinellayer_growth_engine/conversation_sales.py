from __future__ import annotations

from typing import Any, Protocol

from .sales import build_sales_handoff


class SalesTaskStore(Protocol):
    def create_or_get_open_task(self, handoff: dict[str, Any]) -> dict[str, Any]: ...


class ConversationSalesBridge:
    """Translate Conversation evidence into a validated, durable Sales task."""

    def __init__(self, store: SalesTaskStore) -> None:
        self.store = store

    def handle(
        self,
        conversation_handoff: dict[str, Any],
        *,
        priority: str,
        trigger_type: str | None = None,
    ) -> dict[str, Any]:
        classification = conversation_handoff.get("classification", "unclassified")
        action = conversation_handoff.get("recommended_action", "human_review")
        if classification not in {"interested", "question"}:
            return {"status": "not_sales_eligible", "reason": "classification_not_sales_trigger"}

        handoff = build_sales_handoff(
            account_id=str(conversation_handoff["account_id"]),
            person_id=str(conversation_handoff["person_id"]),
            trigger_type=trigger_type or f"conversation_{classification}",
            priority=priority,
            recommended_action=action,
            why_now=conversation_handoff.get("evidence", []),
            latest_reply={
                "classification": classification,
                "conversation_id": conversation_handoff["conversation_id"],
            },
            conversation_summary={
                "conversation_id": conversation_handoff["conversation_id"],
                "state": conversation_handoff.get("conversation_state"),
                "questions": conversation_handoff.get("questions", []),
            },
        )
        task = self.store.create_or_get_open_task(handoff)
        return {"status": "sales_task_created", "handoff": handoff, "task": task}
