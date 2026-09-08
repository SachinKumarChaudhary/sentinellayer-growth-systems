from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

import psycopg

from .recommendations import Recommendation


class ConnectionFactory(Protocol):
    def __call__(self) -> psycopg.Connection[Any]:
        ...


class RecommendationRepository:
    """Persist operator-facing recommendations without executing outreach."""

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def persist(
        self,
        *,
        company_id: int,
        decision_maker_id: str | None,
        recommendation: Recommendation,
        supporting_signal_ids: tuple[str, ...] = (),
        draft_message: str | None = None,
    ) -> dict[str, Any]:
        if company_id <= 0:
            raise ValueError("company_id must be positive")
        if decision_maker_id is not None:
            UUID(decision_maker_id)
        signal_ids = []
        for signal_id in supporting_signal_ids:
            UUID(signal_id)
            signal_ids.append(signal_id)

        now = datetime.now(UTC)
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO growth.recommendations
                    (company_id, decision_maker_id, recommendation_type,
                     recommended_channel, reason, supporting_signal_ids,
                     recommended_sequence, draft_message, confidence,
                     requires_approval, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, 'pending', %s)
                RETURNING recommendation_id, status, created_at
                """,
                (
                    company_id,
                    decision_maker_id,
                    recommendation.recommendation_type,
                    recommendation.recommended_channel,
                    recommendation.reason,
                    signal_ids,
                    json.dumps(recommendation.sequence),
                    draft_message,
                    recommendation.confidence,
                    recommendation.requires_approval,
                    now,
                ),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("recommendation insert returned no row")
            conn.commit()
            return {"recommendation_id": row[0], "status": row[1], "created_at": row[2]}
