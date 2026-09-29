from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable
from uuid import UUID, uuid4

from .state import validate_state_transition


class CRMRepositoryError(RuntimeError):
    """Base error for CRM repository failures."""


class CRMNotFoundError(CRMRepositoryError):
    """Requested canonical CRM entity does not exist."""


class CRMConflictError(CRMRepositoryError):
    """Optimistic concurrency or uniqueness conflict."""


class CRMRepository:
    """Transactional repository for the CRM operator layer."""

    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self._connection_factory = connection_factory

    @staticmethod
    def _json(value: object) -> str:
        return json.dumps(value, default=str)
    @staticmethod
    def _check_version(current: int, expected: int) -> None:
        if current != expected:
            raise CRMConflictError(
                f"version conflict: expected {expected}, current {current}"
            )

    @staticmethod
    def _load_replay(cur: Any, idempotency_key: str | None) -> dict[str, Any] | None:
        if not idempotency_key:
            return None
        cur.execute(
            """
            select after_json
            from crm.audit_events
            where idempotency_key = %s
            """,
            (idempotency_key,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        payload = row["after_json"]
        return dict(payload or {})

    def initialize_account_state(
        self, *, account_id: int, state: str = "NEW",
        actor_user_id: UUID | None = None, request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if state != "NEW":
            raise CRMConflictError("account initialization must start at NEW")
        with self._connection_factory() as conn, conn.cursor() as cur:
            replay = self._load_replay(cur, idempotency_key)
            if replay is not None:
                return replay
            cur.execute(
                "select id from public.companies where id = %s",
                (account_id,),
            )
            if cur.fetchone() is None:
                raise CRMNotFoundError(f"account {account_id} not found")
            cur.execute(
                "select account_id from crm.account_state where account_id = %s for update",
                (account_id,),
            )
            if cur.fetchone() is not None:
                raise CRMConflictError(f"account {account_id} already has CRM state")
            cur.execute(
                """
                insert into crm.account_state(account_id,state)
                values (%s,'NEW')
                returning account_id,state,version,created_at,updated_at
                """,
                (account_id,),
            )
            row = dict(cur.fetchone())
            self._write_history_and_audit(
                cur, "account", str(account_id), None, "NEW",
                actor_user_id, request_id, idempotency_key, row,
            )
            return row
    def transition_account_state(
        self, *, account_id: int, to_state: str, expected_version: int,
        actor_user_id: UUID | None = None, request_id: str | None = None,
        idempotency_key: str | None = None, reason: str | None = None,
        explicit_unsuppress: bool = False,
    ) -> dict[str, Any]:
        return self._transition(
            entity_type="account",
            entity_id=account_id,
            to_state=to_state,
            expected_version=expected_version,
            actor_user_id=actor_user_id,
            request_id=request_id,
            idempotency_key=idempotency_key,
            reason=reason,
            explicit_unsuppress=explicit_unsuppress,
        )

    def transition_contact_state(
        self, *, decision_maker_id: UUID, to_state: str, expected_version: int,
        actor_user_id: UUID | None = None, request_id: str | None = None,
        idempotency_key: str | None = None, reason: str | None = None,
        explicit_unsuppress: bool = False,
    ) -> dict[str, Any]:
        return self._transition(
            entity_type="contact",
            entity_id=decision_maker_id,
            to_state=to_state,
            expected_version=expected_version,
            actor_user_id=actor_user_id,
            request_id=request_id,
            idempotency_key=idempotency_key,
            reason=reason,
            explicit_unsuppress=explicit_unsuppress,
        )

    def _transition(
        self, *, entity_type: str, entity_id: int | UUID, to_state: str,
        expected_version: int, actor_user_id: UUID | None, request_id: str | None,
        idempotency_key: str | None, reason: str | None, explicit_unsuppress: bool,
    ) -> dict[str, Any]:
        table = "crm.account_state" if entity_type == "account" else "crm.contact_state"
        key = "account_id" if entity_type == "account" else "decision_maker_id"
        with self._connection_factory() as conn, conn.cursor() as cur:
            replay = self._load_replay(cur, idempotency_key)
            if replay is not None:
                return replay
            cur.execute(
                f"""
                select {key}, state, version
                from {table}
                where {key} = %s
                for update
                """,
                (entity_id,),
            )
            row = cur.fetchone()
            if row is None:
                if expected_version != 0:
                    raise CRMConflictError(f"{entity_type} {entity_id} is not initialized; expected_version must be 0")
                baseline_state = "NEW" if entity_type == "account" else "NOT_CONTACTED"
                identity_table = "public.companies" if entity_type == "account" else "growth.decision_makers"
                identity_key = "id" if entity_type == "account" else "decision_maker_id"
                cur.execute(
                    f"select {identity_key} from {identity_table} where {identity_key} = %s",
                    (entity_id,),
                )
                if cur.fetchone() is None:
                    raise CRMNotFoundError(f"{entity_type} {entity_id} not found")
                validate_state_transition(
                    entity_type=entity_type,
                    current_state=baseline_state,
                    target_state=to_state,
                    explicit_unsuppress=explicit_unsuppress,
                )
                cur.execute(
                    f"""
                    insert into {table}({key},state,version)
                    values (%s,%s,1)
                    returning {key}, state, version, updated_at
                    """,
                    (entity_id, to_state),
                )
                updated = dict(cur.fetchone())
                self._write_history_and_audit(
                    cur, entity_type, str(entity_id), baseline_state, to_state,
                    actor_user_id, request_id, idempotency_key, updated, reason,
                )
                return updated
            current_state = str(row["state"])
            current_version = int(row["version"])
            self._check_version(current_version, expected_version)
            validate_state_transition(
                entity_type=entity_type,
                current_state=current_state,
                target_state=to_state,
                explicit_unsuppress=explicit_unsuppress,
            )
            new_version = current_version + 1
            cur.execute(
                f"""
                update {table}
                set state = %s, version = %s, updated_at = now()
                where {key} = %s
                returning {key}, state, version, updated_at
                """,
                (to_state, new_version, entity_id),
            )
            updated = dict(cur.fetchone())
            self._write_history_and_audit(
                cur, entity_type, str(entity_id), current_state, to_state,
                actor_user_id, request_id, idempotency_key, updated, reason,
            )
            return updated

    def _write_history_and_audit(
        self, cur: Any, entity_type: str, entity_id: str,
        from_state: str | None, to_state: str,
        actor_user_id: UUID | None, request_id: str | None,
        idempotency_key: str | None, after: dict[str, Any],
        reason: str | None = None,
    ) -> None:
        cur.execute(
            """
            insert into crm.state_history(
                entity_type,entity_id,from_state,to_state,reason,
                actor_user_id,request_id,metadata
            )
            values (%s,%s,%s,%s,%s,%s,%s,'{}'::jsonb)
            """,
            (
                entity_type, entity_id, from_state, to_state, reason,
                actor_user_id, request_id,
            ),
        )
        cur.execute(
            """
            insert into crm.audit_events(
                entity_type,entity_id,action,actor_user_id,request_id,
                idempotency_key,before_json,after_json
            )
            values (%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb)
            """,
            (
                entity_type, entity_id, "state_changed", actor_user_id,
                request_id, idempotency_key,
                self._json({"state": from_state} if from_state else {}),
                self._json(after),
            ),
        )
    def create_note(
        self, *, body: str, author_user_id: UUID,
        account_id: int | None = None, decision_maker_id: UUID | None = None,
        request_id: str | None = None, idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not body.strip():
            raise ValueError("note body must not be empty")
        if (account_id is None) == (decision_maker_id is None):
            raise ValueError("exactly one note target is required")
        with self._connection_factory() as conn, conn.cursor() as cur:
            replay = self._load_replay(cur, idempotency_key)
            if replay is not None:
                return replay
            note_id = str(uuid4())
            cur.execute(
                """
                insert into crm.notes(note_id,account_id,decision_maker_id,body,author_user_id)
                values (%s,%s,%s,%s,%s)
                returning note_id,account_id,decision_maker_id,body,author_user_id,created_at,updated_at
                """,
                (note_id, account_id, decision_maker_id, body.strip(), author_user_id),
            )
            row = dict(cur.fetchone())
            cur.execute(
                """
                insert into crm.audit_events(
                    entity_type,entity_id,action,actor_user_id,request_id,
                    idempotency_key,after_json
                )
                values ('note',%s,'created',%s,%s,%s,%s::jsonb)
                """,
                (
                    note_id, author_user_id, request_id, idempotency_key,
                    self._json(row),
                ),
            )
            return row

    def create_manual_activity(
        self, *, account_id: int, channel: str, activity_type: str,
        occurred_at: datetime, summary: str,
        decision_maker_id: UUID | None = None,
        direction: str = "outbound", reference: str | None = None,
        actor_user_id: UUID | None = None, request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not summary.strip():
            raise ValueError("activity summary must not be empty")
        with self._connection_factory() as conn, conn.cursor() as cur:
            if idempotency_key:
                cur.execute(
                    """
                    select touchpoint_id, company_id, decision_maker_id, channel,
                           touchpoint_type, executed_at, metadata
                    from outreach.touchpoints
                    where idempotency_key = %s
                    """,
                    (idempotency_key,),
                )
                replay = cur.fetchone()
                if replay is not None:
                    return dict(replay)
            touchpoint_id = str(uuid4())
            metadata = {
                "summary": summary.strip(),
                "direction": direction,
                "reference": reference,
                "actor_user_id": str(actor_user_id) if actor_user_id else None,
                "source": "crm",
            }
            cur.execute(
                """
                insert into outreach.touchpoints(
                    touchpoint_id, decision_maker_id, company_id, channel,
                    touchpoint_type, status, executed_at, idempotency_key, metadata
                )
                values (%s,%s,%s,%s,%s,'completed',%s,%s,%s::jsonb)
                returning touchpoint_id,company_id,decision_maker_id,channel,
                    touchpoint_type,status,executed_at,idempotency_key,metadata
                """,
                (
                    touchpoint_id, decision_maker_id, account_id, channel,
                    activity_type, occurred_at, idempotency_key,
                    self._json(metadata),
                ),
            )
            row = dict(cur.fetchone())
            cur.execute(
                """
                insert into crm.audit_events(
                    entity_type,entity_id,action,actor_user_id,request_id,
                    idempotency_key,after_json
                )
                values ('activity',%s,'created',%s,%s,%s,%s::jsonb)
                """,
                (
                    touchpoint_id, actor_user_id, request_id, idempotency_key, self._json(row),
                ),
            )
            return row
    def create_task(
        self, *, account_id: int, recommended_action: str,
        trigger_type: str, priority: str, due_at: datetime | None = None,
        decision_maker_id: UUID | None = None, assigned_to: UUID | None = None,
        why_now: list[Any] | None = None, source_event_type: str | None = None,
        source_event_id: str | None = None,
        actor_user_id: UUID | None = None, request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if not recommended_action.strip():
            raise ValueError("recommended_action must not be empty")
        if priority not in {"P1", "P2", "P3", "P4"}:
            raise ValueError("priority must be P1/P2/P3/P4")
        with self._connection_factory() as conn, conn.cursor() as cur:
            replay = self._load_replay(cur, idempotency_key)
            if replay is not None:
                return replay
            task_id = str(uuid4())
            legacy_person = str(decision_maker_id) if decision_maker_id else None
            cur.execute(
                """
                insert into sales.tasks(
                    sales_task_id,account_id,person_id,canonical_account_id,
                    canonical_person_id,trigger_type,priority,recommended_action,
                    why_now,status,due_at,assigned_to,source_event_type,source_event_id
                )
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,'open',%s,%s,%s,%s)
                returning sales_task_id,canonical_account_id,canonical_person_id,
                          trigger_type,priority,recommended_action,status,due_at,
                          assigned_to,created_at,updated_at
                """,
                (
                    task_id, str(account_id), legacy_person, account_id,
                    decision_maker_id, trigger_type, priority,
                    recommended_action.strip(), self._json(why_now or []),
                    due_at, assigned_to, source_event_type, source_event_id,
                ),
            )
            row = dict(cur.fetchone())
            cur.execute(
                """
                insert into crm.audit_events(
                    entity_type,entity_id,action,actor_user_id,request_id,
                    idempotency_key,after_json
                )
                values ('task',%s,'created',%s,%s,%s,%s::jsonb)
                """,
                (task_id, actor_user_id, request_id, idempotency_key, self._json(row)),
            )
            return row

    def get_user_access(self, *, user_id: UUID) -> dict[str, Any] | None:
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select user_id, role, active, created_at, updated_at
                from crm.user_access
                where user_id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def list_task_queue(self, *, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select sales_task_id, canonical_account_id, canonical_person_id,
                       trigger_type, priority, recommended_action, status,
                       due_at, assigned_to, created_at, updated_at
                from sales.tasks
                where status in ('open','claimed')
                  and canonical_account_id is not null
                order by
                  case when due_at is null then 1 else 0 end,
                  due_at asc,
                  priority asc,
                  created_at asc,
                  sales_task_id asc
                limit %s
                """,
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]

    def assign_account_owner(
        self, *, account_id: int, owner_user_id: UUID | None,
        expected_version: int, actor_user_id: UUID | None = None,
        request_id: str | None = None, idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        with self._connection_factory() as conn, conn.cursor() as cur:
            replay = self._load_replay(cur, idempotency_key)
            if replay is not None:
                return replay
            cur.execute(
                """
                select account_id, state, owner_user_id, version
                from crm.account_state
                where account_id = %s
                for update
                """,
                (account_id,),
            )
            row = cur.fetchone()
            if row is None:
                if expected_version != 0:
                    raise CRMConflictError("account is not initialized; expected_version must be 0")
                cur.execute("select id from public.companies where id = %s", (account_id,))
                if cur.fetchone() is None:
                    raise CRMNotFoundError(f"account {account_id} not found")
                cur.execute(
                    """
                    insert into crm.account_state(account_id,state,owner_user_id,version)
                    values (%s,'NEW',%s,1)
                    returning account_id,state,owner_user_id,version,updated_at
                    """,
                    (account_id, owner_user_id),
                )
                updated = dict(cur.fetchone())
                cur.execute(
                    """
                    insert into crm.audit_events(
                      entity_type,entity_id,action,actor_user_id,request_id,
                      idempotency_key,before_json,after_json
                    ) values ('account',%s,'owner_changed',%s,%s,%s,%s::jsonb,%s::jsonb)
                    """,
                    (
                        str(account_id), actor_user_id, request_id, idempotency_key,
                        self._json({"state": "NEW", "owner_user_id": None, "version": 0}),
                        self._json(updated),
                    ),
                )
                return updated
            self._check_version(int(row["version"]), expected_version)
            new_version = int(row["version"]) + 1
            cur.execute(
                """
                update crm.account_state
                set owner_user_id = %s, version = %s, updated_at = now()
                where account_id = %s
                returning account_id, state, owner_user_id, version, updated_at
                """,
                (owner_user_id, new_version, account_id),
            )
            updated = dict(cur.fetchone())
            cur.execute(
                """
                insert into crm.audit_events(
                  entity_type,entity_id,action,actor_user_id,request_id,
                  idempotency_key,before_json,after_json
                ) values ('account',%s,'owner_changed',%s,%s,%s,%s::jsonb,%s::jsonb)
                """,
                (
                    str(account_id), actor_user_id, request_id, idempotency_key,
                    self._json({"owner_user_id": row["owner_user_id"], "version": row["version"]}),
                    self._json(updated),
                ),
            )
            return updated

    def bulk_transition_accounts(
        self, *, account_ids: list[int], to_state: str,
        expected_versions: dict[int, int], actor_user_id: UUID | None = None,
        request_id: str | None = None, idempotency_key: str | None = None,
        explicit_unsuppress: bool = False,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for account_id in account_ids:
            child_key = f"{idempotency_key}:{account_id}" if idempotency_key else None
            try:
                row = self.transition_account_state(
                    account_id=account_id, to_state=to_state,
                    expected_version=expected_versions.get(account_id, 0),
                    actor_user_id=actor_user_id, request_id=request_id,
                    idempotency_key=child_key,
                    explicit_unsuppress=explicit_unsuppress,
                )
                results.append({"id": account_id, "status": "success", "data": row})
            except CRMRepositoryError as exc:
                results.append({"id": account_id, "status": "failed", "error": str(exc)})
            except Exception as exc:
                results.append({"id": account_id, "status": "failed", "error": str(exc)})
        return results

    def bulk_assign_accounts(
        self, *, account_ids: list[int], owner_user_id: UUID | None,
        expected_versions: dict[int, int], actor_user_id: UUID | None = None,
        request_id: str | None = None, idempotency_key: str | None = None,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for account_id in account_ids:
            child_key = f"{idempotency_key}:{account_id}" if idempotency_key else None
            try:
                row = self.assign_account_owner(
                    account_id=account_id, owner_user_id=owner_user_id,
                    expected_version=expected_versions.get(account_id, 0),
                    actor_user_id=actor_user_id, request_id=request_id,
                    idempotency_key=child_key,
                )
                results.append({"id": account_id, "status": "success", "data": row})
            except CRMRepositoryError as exc:
                results.append({"id": account_id, "status": "failed", "error": str(exc)})
            except Exception as exc:
                results.append({"id": account_id, "status": "failed", "error": str(exc)})
        return results
