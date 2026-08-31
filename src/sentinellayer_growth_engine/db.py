from __future__ import annotations

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
        outcome = "accepted" if accepted else "permanent_failure"
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
