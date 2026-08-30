from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import dict_row


@dataclass(frozen=True)
class ClaimedSend:
    send_id: str
    person_id: int
    campaign_id: str
    sequence_step_id: str
    mailbox_id: str
    scheduled_at: Any


class Database:
    """Thin PostgreSQL access layer.

    Business rules stay in services; this class owns parameterized SQL and
    transaction boundaries only.
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def connection(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def claim_due_sends(self, batch_size: int = 20) -> Sequence[ClaimedSend]:
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
            ClaimedSend(
                send_id=str(row["send_id"]),
                person_id=int(row["person_id"]),
                campaign_id=str(row["campaign_id"]),
                sequence_step_id=str(row["sequence_step_id"]),
                mailbox_id=str(row["mailbox_id"]),
                scheduled_at=row["scheduled_at"],
            )
            for row in rows
        ]

    def is_suppressed(self, email: str) -> bool:
        with self.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("select public.is_suppressed(%s)", (email,))
                result = cur.fetchone()
                return bool(result[0]) if result is not None else True
