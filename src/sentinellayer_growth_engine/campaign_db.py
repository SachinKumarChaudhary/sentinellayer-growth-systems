from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

import psycopg
from psycopg.rows import dict_row


class CampaignClaimStore(Protocol):
    def claim_step(self, enrollment_id: str, worker_id: str, lease_seconds: int = 300) -> dict[str, Any] | None: ...
    def release_step(self, enrollment_id: str, claim_token: str) -> bool: ...
    def complete_step(self, enrollment_id: str, claim_token: str, step_no: int, next_action_at: datetime) -> bool: ...


class CampaignDatabase:
    """PostgreSQL persistence for campaign step claims.

    Claims are short-lived leases. The Campaign system never sends mail from
    this repository; it only reserves a sequence step for rendering and
    downstream handoff.
    """

    def __init__(self, dsn: str, worker_id: str) -> None:
        if not worker_id.strip():
            raise ValueError("worker_id must not be empty")
        self._dsn = dsn
        self._worker_id = worker_id

    def _connection(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def claim_step(
        self,
        enrollment_id: str,
        worker_id: str | None = None,
        lease_seconds: int = 300,
    ) -> dict[str, Any] | None:
        UUID(enrollment_id)
        effective_worker = self._worker_id if worker_id is None else worker_id
        if not effective_worker.strip():
            raise ValueError("worker_id must not be empty")

        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                "select * from public.claim_campaign_step(%s, %s, %s)",
                (enrollment_id, effective_worker, lease_seconds),
            )
            return cur.fetchone()

    def release_step(self, enrollment_id: str, claim_token: str) -> bool:
        UUID(enrollment_id)
        UUID(claim_token)
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                "select public.release_campaign_step_claim(%s, %s)",
                (enrollment_id, claim_token),
            )
            row = cur.fetchone()
            return bool(row[0]) if row else False

    def complete_step(
        self,
        enrollment_id: str,
        claim_token: str,
        step_no: int,
        next_action_at: datetime,
    ) -> bool:
        UUID(enrollment_id)
        UUID(claim_token)
        if step_no < 1:
            raise ValueError("step_no must be positive")
        if next_action_at.tzinfo is None:
            raise ValueError("next_action_at must be timezone-aware")

        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                "select public.complete_campaign_step_claim(%s, %s, %s, %s)",
                (enrollment_id, claim_token, step_no, next_action_at),
            )
            row = cur.fetchone()
            return bool(row[0]) if row else False
