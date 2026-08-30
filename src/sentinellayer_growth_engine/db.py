from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .engine import DueSend


@dataclass(frozen=True)
class ClaimedSend:
    send_id: str
    person_id: int
    campaign_id: str
    sequence_step_id: str
    mailbox_id: str
    scheduled_at: datetime
    sender: str
    recipient: str
    subject: str
    body_text: str
    message_id: str


class Database:
    """PostgreSQL repository; durable state transitions stay in SQL."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def connection(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def claim_due_sends(self, batch_size: int = 20) -> list[DueSend]:
        if batch_size < 1:
            raise ValueError("batch_size must be >= 1")

        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "select * from public.claim_due_sends(%s)",
                    (batch_size,),
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
            )
            for row in rows
        ]

    def is_suppressed(self, email: str) -> bool:
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select public.is_suppressed(%s)", (email,))
                row = cur.fetchone()
                return bool(row[0]) if row is not None else True
