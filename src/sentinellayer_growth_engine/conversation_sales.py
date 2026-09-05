from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from .sales import SalesHandoffError, build_sales_handoff


class SalesTaskStore(Protocol):
    def upsert_open_task(self, handoff: Mapping[str, Any]) -> dict[str, Any]:
        ...


class ConversationSalesBridge:
    """Translate approved Conversation handoffs into durable human sales tasks."""

    TRIGGERS = frozenset({"interested", "question"})

    def __init__(self, task_store: SalesTaskStore) -> None:
        self.task_store = task_store

    def bridge(
        self,
        conversation: Mapping[str, Any],
        *,
        priority: str,
        why_now: list[Any] | None = None,
        behavior_summary: list[Any] | None = None,
        campaign_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        classification = str(conversation.get("classification") or "unclassified")
        if classification not in self.TRIGGERS:
            raise SalesHandoffError(
                f"conversation classification {classification!r} does not create a sales task"
            )

        handoff = build_sales_handoff(
            account_id=str(conversation["account_id"]),
            person_id=str(conversation["person_id"]),
            trigger_type=classification,
            priority=priority,
            recommended_action=str(conversation["recommended_action"]),
            why_now=why_now or [{"signal": classification}],
            latest_reply=dict(conversation),
            behavior_summary=behavior_summary,
            campaign_context=campaign_context,
            conversation_summary={
                "conversation_id": str(conversation["conversation_id"]),
                "classification": classification,
                "state": conversation.get("conversation_state"),
            },
        )
        return self.task_store.upsert_open_task(handoff)
