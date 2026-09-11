from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from .linkedin_outreach import LinkedInContact, LinkedInTouchpoint, next_state_after_observation


class LinkedInOutreachDatabaseError(ValueError):
    """Raised when LinkedIn outreach persistence is invalid or unsafe."""


class LinkedInOutreachDatabase:
    """Persistence adapter over the canonical growth/outreach tables.

    This layer only records planned/observed state. It never performs a LinkedIn
    network action itself. A concrete provider must be invoked by a separate
    execution adapter after the sequence has passed the approval gate.
    """

    def __init__(self, dsn: str) -> None:
        if not dsn.strip():
            raise ValueError("dsn must not be empty")
        self._dsn = dsn

    def _connection(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def approve_sequence(self, *, sequence_id: str, approved_by: str, notes: str | None = None) -> None:
        UUID(sequence_id)
        if not approved_by.strip():
            raise ValueError("approved_by must not be empty")
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                update outreach.sequences
                   set status = 'approved'
                 where sequence_id = %s
                   and status = 'draft'
                returning sequence_id
                """,
                (sequence_id,),
            )
            if cur.fetchone() is None:
                raise LinkedInOutreachDatabaseError("sequence is not in draft state")
            cur.execute(
                """
                insert into outreach.sequence_approvals
                    (sequence_id, decision, approved_by, notes)
                values (%s, 'approved', %s, %s)
                """,
                (sequence_id, approved_by, notes),
            )

    def create_touchpoints(
        self,
        *,
        sequence_id: str,
        enrollment_id: str,
        contact: LinkedInContact,
        touchpoints: list[LinkedInTouchpoint],
    ) -> int:
        UUID(sequence_id)
        UUID(enrollment_id)
        if not touchpoints:
            raise ValueError("touchpoints must not be empty")
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                "select status from outreach.sequences where sequence_id = %s",
                (sequence_id,),
            )
            sequence = cur.fetchone()
            if sequence is None or sequence["status"] != "approved":
                raise LinkedInOutreachDatabaseError("LinkedIn touchpoints require an approved sequence")

            inserted = 0
            for point in touchpoints:
                metadata = dict(point.metadata)
                metadata["linkedin_url"] = contact.linkedin_url
                cur.execute(
                    """
                    insert into outreach.touchpoints
                        (enrollment_id, decision_maker_id, company_id, sequence_id,
                         channel, touchpoint_type, status, scheduled_at,
                         provider, idempotency_key, metadata)
                    values
                        (%s, %s, %s, %s, 'linkedin', %s, %s, %s,
                         %s, %s, %s::jsonb)
                    on conflict (idempotency_key) do nothing
                    """,
                    (
                        enrollment_id,
                        contact.decision_maker_id,
                        contact.company_id,
                        sequence_id,
                        point.touchpoint_type,
                        point.status,
                        point.scheduled_at,
                        "operator",
                        point.idempotency_key,
                        json.dumps(metadata),
                    ),
                )
                inserted += cur.rowcount
            return inserted

    def update_contact_state(
        self,
        *,
        enrollment_id: str,
        decision_maker_id: str,
        state: str,
        next_action_at: datetime | None,
        last_contacted_at: datetime | None = None,
        last_replied_at: datetime | None = None,
        notes: str | None = None,
    ) -> None:
        UUID(enrollment_id)
        UUID(decision_maker_id)
        allowed = {
            "not_contacted",
            "active",
            "awaiting_reply",
            "replied",
            "follow_up_due",
            "meeting",
            "closed",
            "suppressed",
        }
        if state not in allowed:
            raise LinkedInOutreachDatabaseError(f"unsupported contact state: {state}")
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                update growth.contact_campaign_states
                   set state = %s,
                       next_action_at = %s,
                       last_contacted_at = coalesce(%s, last_contacted_at),
                       last_replied_at = coalesce(%s, last_replied_at),
                       notes = coalesce(%s, notes),
                       updated_at = now()
                 where enrollment_id = %s
                   and decision_maker_id = %s
                returning contact_campaign_state_id
                """,
                (
                    state,
                    next_action_at,
                    last_contacted_at,
                    last_replied_at,
                    notes,
                    enrollment_id,
                    decision_maker_id,
                ),
            )
            if cur.fetchone() is None:
                raise LinkedInOutreachDatabaseError("contact campaign state does not exist")

    def record_execution_attempt(
        self,
        *,
        touchpoint_id: str,
        provider: str | None,
        result: str,
        provider_error_code: str | None,
        started_at: datetime | None,
        finished_at: datetime | None,
        metadata: Mapping[str, Any],
    ) -> int:
        UUID(touchpoint_id)
        if not result.strip():
            raise ValueError("result must not be empty")
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select execution_attempt_id
                  from outreach.touchpoints
                 where touchpoint_id = %s
                 for update
                """,
                (touchpoint_id,),
            )
            if cur.fetchone() is None:
                raise LinkedInOutreachDatabaseError("touchpoint not found")
            cur.execute(
                """
                select coalesce(max(attempt_number), 0) + 1 as next_attempt
                  from outreach.execution_attempts
                 where touchpoint_id = %s
                """,
                (touchpoint_id,),
            )
            attempt_number = int(cur.fetchone()["next_attempt"])
            cur.execute(
                """
                insert into outreach.execution_attempts
                    (touchpoint_id, attempt_number, provider, result,
                     provider_error_code, started_at, finished_at, metadata)
                values (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    touchpoint_id,
                    attempt_number,
                    provider,
                    result,
                    provider_error_code,
                    started_at,
                    finished_at,
                    json.dumps(dict(metadata)),
                ),
            )
            return attempt_number

    def record_touchpoint_observation(
        self,
        *,
        touchpoint_id: str,
        status: str,
        provider: str,
        provider_reference: str | None,
        metadata: Mapping[str, Any],
        executed_at: datetime | None,
    ) -> None:
        UUID(touchpoint_id)
        allowed = {"planned", "approved", "queued", "sent", "delivered", "failed", "cancelled", "completed"}
        if status not in allowed:
            raise LinkedInOutreachDatabaseError(f"unsupported touchpoint status: {status}")
        if not provider.strip():
            raise ValueError("provider must not be empty")
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                update outreach.touchpoints
                   set status = %s,
                       provider = %s,
                       provider_reference = %s,
                       metadata = metadata || %s::jsonb,
                       executed_at = coalesce(%s, executed_at)
                 where touchpoint_id = %s
                returning touchpoint_id
                """,
                (
                    status,
                    provider,
                    provider_reference,
                    json.dumps(dict(metadata)),
                    executed_at,
                    touchpoint_id,
                ),
            )
            if cur.fetchone() is None:
                raise LinkedInOutreachDatabaseError("touchpoint not found")

    def apply_observation(
        self,
        *,
        touchpoint_id: str,
        observation: Mapping[str, Any],
        now: datetime,
    ) -> str:
        """Persist a provider/operator observation and project the relationship state."""
        UUID(touchpoint_id)
        if now.tzinfo is None:
            raise LinkedInOutreachDatabaseError("now must be timezone-aware")
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select enrollment_id, decision_maker_id
                  from outreach.touchpoints
                 where touchpoint_id = %s
                """,
                (touchpoint_id,),
            )
            touchpoint = cur.fetchone()
            if touchpoint is None:
                raise LinkedInOutreachDatabaseError("touchpoint not found")
            cur.execute(
                """
                select state, next_action_at
                  from growth.contact_campaign_states
                 where enrollment_id = %s
                   and decision_maker_id = %s
                """,
                (touchpoint["enrollment_id"], touchpoint["decision_maker_id"]),
            )
            current = cur.fetchone()
            if current is None:
                raise LinkedInOutreachDatabaseError("contact campaign state does not exist")

            update = next_state_after_observation(
                current_state=current["state"],
                observation=observation,
                now=now,
                next_action_at=current["next_action_at"],
            )
            event = str(observation.get("event", "")).strip().lower()
            inbound = bool(observation.get("inbound_message", False))
            last_contacted_at = now if event in {"connection_request_sent", "message_sent"} else None
            last_replied_at = now if inbound else None
            notes = update.reason
            cur.execute(
                """
                update growth.contact_campaign_states
                   set state = %s,
                       next_action_at = %s,
                       last_contacted_at = coalesce(%s, last_contacted_at),
                       last_replied_at = coalesce(%s, last_replied_at),
                       notes = %s,
                       updated_at = now()
                 where enrollment_id = %s
                   and decision_maker_id = %s
                """,
                (
                    update.state,
                    update.next_action_at,
                    last_contacted_at,
                    last_replied_at,
                    notes,
                    touchpoint["enrollment_id"],
                    touchpoint["decision_maker_id"],
                ),
            )
            observation_metadata = {
                "last_observation": dict(observation),
                "observed_at": now.isoformat(),
                "observation_reason": update.reason,
            }
            cur.execute(
                """
                update outreach.touchpoints
                   set metadata = metadata || %s::jsonb
                 where touchpoint_id = %s
                """,
                (json.dumps(observation_metadata), touchpoint_id),
            )
            return update.state
