from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .engine import DueSend


class Database:
    """PostgreSQL repository; durable state transitions stay in SQL."""

    def __init__(self, dsn: str, worker_id: str = "worker") -> None:
        self._dsn = dsn
        if not worker_id.strip():
            raise ValueError("worker_id must not be empty")
        self._worker_id = worker_id

    def connection(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def get_control_state(self) -> dict[str, object]:
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select environment, outbound_state, maintenance_mode,
                       updated_at, updated_by
                from operations.control_state
                where singleton = true
                """
            )
            row = cur.fetchone()
        if row is None:
            raise RuntimeError("operations control state is missing")
        return dict(row)

    def upsert_open_task(self, handoff: dict[str, object]) -> dict[str, object]:
        """SalesTaskStore-compatible alias for the Conversation→Sales bridge."""
        return self.upsert_open_sales_task(handoff)

    def persist_handoff(
        self,
        *,
        handoff: dict[str, object],
        sender_email: str,
        subject: str,
        body_text: str,
        provider_message_id: str,
        thread_key: str,
        received_at: datetime,
    ) -> dict[str, object]:
        """Persist a normalized Conversation handoff idempotently."""
        conversation_id = str(handoff["conversation_id"])
        person_id = str(handoff["person_id"])
        account_id = str(handoff["account_id"])
        classification = str(handoff["classification"])

        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into conversation.threads (
                    conversation_id, account_id, person_id, thread_key,
                    state, last_message_at, updated_at
                ) values (%s,%s,%s,%s,'action_selected',%s,now())
                on conflict (thread_key) do update
                set state='action_selected',
                    last_message_at=greatest(conversation.threads.last_message_at, excluded.last_message_at),
                    updated_at=now()
                returning conversation_id
                """,
                (conversation_id, account_id, person_id, thread_key, received_at),
            )
            thread_row = cur.fetchone()
            if thread_row is None:
                raise RuntimeError("conversation thread upsert returned no row")
            durable_conversation_id = str(thread_row["conversation_id"])

            cur.execute(
                """
                insert into conversation.replies (
                    reply_id, conversation_id, provider_message_id, account_id,
                    person_id, source_send_id, sender_email, subject, body_text,
                    classification, received_at
                ) values (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                )
                on conflict (provider_message_id) do nothing
                returning reply_id
                """,
                (
                    handoff["reply_id"],
                    durable_conversation_id,
                    provider_message_id,
                    account_id,
                    person_id,
                    handoff.get("source_send_id"),
                    sender_email,
                    subject,
                    body_text,
                    classification,
                    received_at,
                ),
            )
            reply_row = cur.fetchone()
            if reply_row is None:
                cur.execute(
                    """
                    select reply_id
                    from conversation.replies
                    where provider_message_id=%s
                    """,
                    (provider_message_id,),
                )
                reply_row = cur.fetchone()
                if reply_row is None:
                    raise RuntimeError("conversation reply dedupe lookup returned no row")
                return {
                    "conversation_id": durable_conversation_id,
                    "reply_id": str(reply_row["reply_id"]),
                    "status": "duplicate",
                }

        return {
            "conversation_id": durable_conversation_id,
            "reply_id": str(reply_row["reply_id"]),
            "status": "stored",
        }

    def add_suppression(self, *, email: str, reason: str) -> None:
        """Permanently suppress an email address after a deterministic stop signal."""
        normalized = email.strip().lower()
        if not normalized or "@" not in normalized:
            raise ValueError("email must be valid")
        if not reason.strip():
            raise ValueError("reason must not be empty")
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into public.suppression (email, reason, added_at)
                values (%s, %s, now())
                on conflict (email) do update
                set reason=excluded.reason, added_at=excluded.added_at
                """,
                (normalized, reason),
            )

    def cancel_future_sends_for_person(self, *, person_id: int, reason: str) -> None:
        """Cancel future queued campaign sends for a person."""
        if person_id <= 0:
            raise ValueError("person_id must be positive")
        if not reason.strip():
            raise ValueError("reason must not be empty")
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "select public.cancel_future_sends_for_person(%s, %s)",
                (person_id, reason),
            )

    def upsert_open_sales_task(self, handoff: dict[str, object]) -> dict[str, object]:
        required = ("sales_task_id", "account_id", "person_id", "trigger_type", "priority", "recommended_action")
        missing = [key for key in required if not handoff.get(key)]
        if missing:
            raise ValueError("sales handoff missing: " + ", ".join(missing))
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into sales.tasks (
                    sales_task_id, account_id, person_id, trigger_type, priority,
                    recommended_action, why_now, latest_reply, behavior_summary,
                    campaign_context, conversation_summary, status, updated_at
                ) values (
                    %s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,now()
                )
                on conflict (account_id, person_id, trigger_type)
                where sales.tasks.status in ('open','claimed')
                do update set
                    priority = excluded.priority,
                    recommended_action = excluded.recommended_action,
                    why_now = excluded.why_now,
                    latest_reply = excluded.latest_reply,
                    behavior_summary = excluded.behavior_summary,
                    campaign_context = excluded.campaign_context,
                    conversation_summary = excluded.conversation_summary,
                    updated_at = now()
                returning sales_task_id, account_id, person_id, trigger_type,
                          priority, recommended_action, status, created_at, updated_at
                """,
                (
                    handoff["sales_task_id"],
                    handoff["account_id"],
                    handoff["person_id"],
                    handoff["trigger_type"],
                    handoff["priority"],
                    handoff["recommended_action"],
                    json.dumps(handoff.get("why_now") or []),
                    json.dumps(handoff.get("latest_reply")),
                    json.dumps(handoff.get("behavior_summary")),
                    json.dumps(handoff.get("campaign_context")),
                    json.dumps(handoff.get("conversation_summary")),
                    "open",
                ),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("SalesTaskStore upsert returned no row")
        return dict(row)

    def claim_due(self, *, batch_size: int = 20, worker_id: str | None = None) -> list[DueSend]:
        if batch_size < 1 or batch_size > 500:
            raise ValueError("batch_size must be between 1 and 500")
        effective_worker_id = self._worker_id if worker_id is None else worker_id
        if not effective_worker_id.strip():
            raise ValueError("worker_id must not be empty")

        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "select * from public.claim_due_sends(%s, %s)",
                (batch_size, effective_worker_id),
            )
            rows = cur.fetchall()

        return [
            DueSend(
                send_id=str(row["send_id"]),
                sender=str(row["sender"]),
                recipient=str(row["recipient"]),
                subject=str(row["subject"]),
                body_text=str(row["body_text"]),
                message_id=str(row["message_id"]),
                attempt_count=int(row["attempt_count"]),
                headers={str(k): str(v) for k, v in dict(row.get("rendered_headers") or {}).items()},
                reply_to=str(row["reply_to"]) if row.get("reply_to") else None,
            )
            for row in rows
        ]

    def claim_due_sends(self, batch_size: int = 20, worker_id: str | None = None) -> list[DueSend]:
        return self.claim_due(batch_size=batch_size, worker_id=worker_id)

    def mark_sent(
        self,
        *,
        send_id: str,
        message_id: str,
        provider_message_id: str | None,
    ) -> None:
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "select public.record_send_attempt(%s, 'accepted', %s, null, null, null, '{}'::jsonb, %s)",
                (send_id, provider_message_id or message_id, self._worker_id),
            )

    def resolve_uncertain(self, *, send_id: str, accepted: bool, provider_message_id: str | None = None, error: str | None = None) -> None:
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "select public.resolve_uncertain_send(%s, %s, %s, %s)",
                (send_id, accepted, provider_message_id, error),
            )

    def mark_ambiguous(self, *, send_id: str, error: str) -> None:
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "select public.record_send_attempt(%s, 'ambiguous', null, null, %s, null, '{}'::jsonb, %s)",
                (send_id, error, self._worker_id),
            )

    def mark_failed(
        self,
        *,
        send_id: str,
        error: str,
        retry_at: datetime | None,
        transient: bool = False,
        provider_code: str | None = None,
    ) -> None:
        outcome = "temporary_failure" if transient and retry_at is not None else "permanent_failure"
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "select public.record_send_attempt(%s, %s, null, %s, %s, %s, '{}'::jsonb, %s)",
                (send_id, outcome, provider_code, error, retry_at, self._worker_id),
            )

    def is_suppressed(self, email: str) -> bool:
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute("select public.is_suppressed(%s)", (email,))
            row = cur.fetchone()
            return bool(row[0]) if row is not None else True

    def cancel_future_sends(self, *, person_id: int, reason: str) -> None:
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "select public.cancel_future_sends_for_person(%s, %s)",
                (person_id, reason),
            )
