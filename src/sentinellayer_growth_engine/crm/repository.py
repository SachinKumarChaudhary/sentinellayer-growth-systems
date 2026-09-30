from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Callable
from uuid import UUID, uuid4

from .state import EntityType, validate_state_transition


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
        self, *, entity_type: EntityType, entity_id: int | UUID, to_state: str,
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

    def update_account_fields(
        self, *, account_id: int, fields: dict[str, Any], actor_user_id: UUID,
        request_id: str | None = None, idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        allowed = {
            "name": "name",
            "domain": "domain",
            "website": "website",
            "company_linkedin": "company_linkedin",
            "country": "country",
            "city": "city",
            "segment": "segment",
            "revenue_est": "revenue_est",
            "visits_est": "visits_est",
            "notes": "notes",
        }
        clean = {key: value for key, value in fields.items() if key in allowed}
        if not clean:
            raise ValueError("no editable account fields supplied")
        if "domain" in clean and not str(clean["domain"]).strip():
            raise ValueError("domain must not be empty")
        if "name" in clean and clean["name"] is not None and not str(clean["name"]).strip():
            raise ValueError("name must not be empty when provided")
        with self._connection_factory() as conn, conn.cursor() as cur:
            replay = self._load_replay(cur, idempotency_key)
            if replay is not None:
                return replay
            cur.execute("select id, name, domain, website, company_linkedin, country, city, segment, revenue_est, visits_est, notes from public.companies where id = %s for update", (account_id,))
            row = cur.fetchone()
            if row is None:
                raise CRMNotFoundError(f"account {account_id} not found")
            before = {key: row.get(key) for key in clean}
            sets = []
            params: list[Any] = []
            for key, value in clean.items():
                sets.append(f"{allowed[key]} = %s")
                params.append(value)
            sets.append("updated_at = now()")
            params.append(account_id)
            cur.execute(
                f"update public.companies set {', '.join(sets)} where id = %s returning id, name, domain, website, company_linkedin, country, city, segment, revenue_est, visits_est, notes, updated_at",
                params,
            )
            updated = dict(cur.fetchone())
            after = {key: updated.get(key) for key in clean}
            cur.execute(
                """
                insert into crm.audit_events(
                  entity_type, entity_id, action, actor_user_id, request_id,
                  idempotency_key, before_json, after_json, metadata
                ) values ('account', %s, 'fields_updated', %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
                """,
                (
                    str(account_id), actor_user_id, request_id, idempotency_key,
                    self._json(before), self._json(after), self._json({"fields": list(clean)}),
                ),
            )
            return updated

    def update_contact_fields(
        self, *, decision_maker_id: UUID, fields: dict[str, Any], actor_user_id: UUID,
        request_id: str | None = None, idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        allowed = {
            "full_name": "full_name",
            "title": "title",
            "role_family": "role_family",
            "role_priority": "role_priority",
            "rationale": "rationale",
        }
        clean = {key: value for key, value in fields.items() if key in allowed}
        if not clean:
            raise ValueError("no editable contact fields supplied")
        if "full_name" in clean and not str(clean["full_name"]).strip():
            raise ValueError("full_name must not be empty")
        with self._connection_factory() as conn, conn.cursor() as cur:
            replay = self._load_replay(cur, idempotency_key)
            if replay is not None:
                return replay
            cur.execute(
                "select decision_maker_id, company_id, full_name, title, role_family, role_priority, rationale from growth.decision_makers where decision_maker_id = %s for update",
                (decision_maker_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise CRMNotFoundError(f"contact {decision_maker_id} not found")
            before = {key: row.get(key) for key in clean}
            sets = []
            params: list[Any] = []
            for key, value in clean.items():
                sets.append(f"{allowed[key]} = %s")
                params.append(value)
            sets.append("updated_at = now()")
            params.append(decision_maker_id)
            cur.execute(
                f"update growth.decision_makers set {', '.join(sets)} where decision_maker_id = %s returning decision_maker_id, company_id, full_name, title, role_family, role_priority, rationale, status, research_status, confidence, last_verified_at, updated_at",
                params,
            )
            updated = dict(cur.fetchone())
            after = {key: updated.get(key) for key in clean}
            cur.execute(
                """
                insert into crm.audit_events(
                  entity_type, entity_id, action, actor_user_id, request_id,
                  idempotency_key, before_json, after_json, metadata
                ) values ('contact', %s, 'fields_updated', %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb)
                """,
                (
                    str(decision_maker_id), actor_user_id, request_id, idempotency_key,
                    self._json(before), self._json(after), self._json({"fields": list(clean)}),
                ),
            )
            return updated

    def export_records(self, *, entity: str, limit: int = 5000) -> list[dict[str, Any]]:
        if entity == 'accounts':
            sql="""select c.id, c.name, c.domain, c.website, c.company_linkedin, c.country, c.city, c.segment, c.revenue_est, c.visits_est, coalesce(s.state,'NEW') as crm_state, s.owner_user_id, c.created_at, c.updated_at from public.companies c left join crm.account_state s on s.account_id=c.id order by c.id limit %s"""
        elif entity == 'contacts':
            sql="""select dm.decision_maker_id, dm.company_id, c.name as company_name, dm.full_name, dm.title, dm.role_family, dm.role_priority, dm.status, dm.research_status, dm.confidence, coalesce(cs.state,'NOT_CONTACTED') as crm_state, cs.owner_user_id, dm.created_at, dm.updated_at from growth.decision_makers dm join public.companies c on c.id=dm.company_id left join crm.contact_state cs on cs.decision_maker_id=dm.decision_maker_id order by dm.created_at desc limit %s"""
        elif entity == 'opportunities':
            sql="""select o.opportunity_id, o.account_id, c.name as account_name, o.primary_contact_id, o.owner_user_id, o.name, o.stage, o.value, o.currency, o.expected_close_date, o.next_task_id, o.closed_at, o.closed_reason, o.version, o.created_at, o.updated_at from crm.opportunities o join public.companies c on c.id=o.account_id order by o.updated_at desc limit %s"""
        elif entity == 'tasks':
            sql="""select sales_task_id, canonical_account_id, canonical_person_id, trigger_type, priority, recommended_action, status, due_at, assigned_to, created_at, updated_at from sales.tasks where canonical_account_id is not null order by created_at desc limit %s"""
        else:
            raise ValueError('unsupported export entity')
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(sql,(limit,)); return [dict(row) for row in cur.fetchall()]

    def list_opportunities(self, *, account_id: int | None = None, owner_user_id: UUID | None = None, stage: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        where = ["1=1"]
        params: list[Any] = []
        if account_id is not None:
            where.append("o.account_id = %s"); params.append(account_id)
        if owner_user_id is not None:
            where.append("o.owner_user_id = %s"); params.append(owner_user_id)
        if stage:
            where.append("o.stage = %s"); params.append(stage)
        params.append(limit)
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(f"""
                select o.opportunity_id, o.account_id, c.name as account_name, c.domain,
                       o.primary_contact_id, dm.full_name as primary_contact_name,
                       o.owner_user_id, u.email as owner_email, o.name, o.stage, o.value,
                       o.currency, o.expected_close_date, o.next_task_id, o.notes,
                       o.closed_at, o.closed_reason, o.version, o.created_at, o.updated_at
                from crm.opportunities o
                join public.companies c on c.id = o.account_id
                left join growth.decision_makers dm on dm.decision_maker_id = o.primary_contact_id
                left join auth.users u on u.id = o.owner_user_id
                where {' and '.join(where)}
                order by case when o.stage in ('WON','LOST') then 1 else 0 end,
                         o.updated_at desc, o.opportunity_id asc
                limit %s
            """, params)
            return [dict(row) for row in cur.fetchall()]

    def get_opportunity(self, *, opportunity_id: UUID) -> dict[str, Any]:
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute("""
                select o.opportunity_id, o.account_id, c.name as account_name, c.domain,
                       o.primary_contact_id, dm.full_name as primary_contact_name, dm.title as primary_contact_title,
                       o.owner_user_id, u.email as owner_email, o.name, o.stage, o.value,
                       o.currency, o.expected_close_date, o.next_task_id, o.notes,
                       o.closed_at, o.closed_reason, o.version, o.created_at, o.updated_at
                from crm.opportunities o
                join public.companies c on c.id = o.account_id
                left join growth.decision_makers dm on dm.decision_maker_id = o.primary_contact_id
                left join auth.users u on u.id = o.owner_user_id
                where o.opportunity_id = %s
            """, (opportunity_id,))
            row = cur.fetchone()
            if row is None:
                raise CRMNotFoundError(f"opportunity {opportunity_id} not found")
            return dict(row)

    def create_opportunity(self, *, account_id: int, name: str, owner_user_id: UUID, actor_user_id: UUID,
                           primary_contact_id: UUID | None = None, stage: str = 'QUALIFIED',
                           value: Any = None, currency: str | None = None, expected_close_date: Any = None,
                           next_task_id: UUID | None = None, notes: str | None = None,
                           closed_reason: str | None = None, request_id: str | None = None,
                           idempotency_key: str | None = None) -> dict[str, Any]:
        if not str(name).strip():
            raise ValueError('opportunity name must not be empty')
        allowed_stages={'QUALIFIED','DISCOVERY','EVALUATION','PROPOSAL','NEGOTIATION','WON','LOST'}
        if stage not in allowed_stages:
            raise ValueError('invalid opportunity stage')
        with self._connection_factory() as conn, conn.cursor() as cur:
            replay=self._load_replay(cur,idempotency_key)
            if replay is not None: return replay
            cur.execute("select user_id from crm.user_access where user_id=%s and active=true",(owner_user_id,))
            if cur.fetchone() is None: raise CRMConflictError('opportunity owner must be an active CRM member')
            cur.execute("select id from public.companies where id=%s",(account_id,))
            if cur.fetchone() is None: raise CRMNotFoundError(f'account {account_id} not found')
            if primary_contact_id is not None:
                cur.execute("select 1 from growth.decision_makers where decision_maker_id=%s and company_id=%s",(primary_contact_id,account_id))
                if cur.fetchone() is None: raise CRMConflictError('primary contact must belong to opportunity account')
            closed_at = datetime.now().astimezone() if stage in {'WON','LOST'} else None
            cur.execute("""
                insert into crm.opportunities(account_id,primary_contact_id,owner_user_id,name,stage,value,currency,expected_close_date,next_task_id,notes,closed_at,closed_reason)
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                returning opportunity_id,account_id,primary_contact_id,owner_user_id,name,stage,value,currency,expected_close_date,next_task_id,notes,closed_at,closed_reason,version,created_at,updated_at
            """,(account_id,primary_contact_id,owner_user_id,name.strip(),stage,value,currency,expected_close_date,next_task_id,notes,closed_at,closed_reason))
            row=dict(cur.fetchone())
            cur.execute("""insert into crm.audit_events(entity_type,entity_id,action,actor_user_id,request_id,idempotency_key,after_json) values ('opportunity',%s,'created',%s,%s,%s,%s::jsonb)""",(str(row['opportunity_id']),actor_user_id,request_id,idempotency_key,self._json(row)))
            return row

    def update_opportunity(self, *, opportunity_id: UUID, fields: dict[str, Any], expected_version: int, actor_user_id: UUID,
                           request_id: str | None = None, idempotency_key: str | None = None) -> dict[str, Any]:
        allowed={'name','primary_contact_id','owner_user_id','value','currency','expected_close_date','next_task_id','notes'}
        clean={k:v for k,v in fields.items() if k in allowed}
        if not clean: raise ValueError('no editable opportunity fields supplied')
        with self._connection_factory() as conn, conn.cursor() as cur:
            replay=self._load_replay(cur,idempotency_key)
            if replay is not None: return replay
            cur.execute("select * from crm.opportunities where opportunity_id=%s for update",(opportunity_id,))
            row=cur.fetchone()
            if row is None: raise CRMNotFoundError(f'opportunity {opportunity_id} not found')
            self._check_version(int(row['version']),expected_version)
            account_id=int(row['account_id'])
            if 'owner_user_id' in clean:
                owner=clean['owner_user_id']
                cur.execute("select 1 from crm.user_access where user_id=%s and active=true",(owner,))
                if cur.fetchone() is None: raise CRMConflictError('opportunity owner must be an active CRM member')
            if 'primary_contact_id' in clean and clean['primary_contact_id'] is not None:
                cur.execute("select 1 from growth.decision_makers where decision_maker_id=%s and company_id=%s",(clean['primary_contact_id'],account_id))
                if cur.fetchone() is None: raise CRMConflictError('primary contact must belong to opportunity account')
            params=[]; sets=[]
            for key,val in clean.items(): sets.append(f"{key}=%s"); params.append(val)
            sets.append('version=%s'); params.append(int(row['version'])+1); sets.append('updated_at=now()'); params.append(opportunity_id)
            cur.execute(f"update crm.opportunities set {', '.join(sets)} where opportunity_id=%s returning *",params)
            updated=dict(cur.fetchone())
            before={k:row.get(k) for k in clean}
            after={k:updated.get(k) for k in clean}
            cur.execute("""insert into crm.audit_events(entity_type,entity_id,action,actor_user_id,request_id,idempotency_key,before_json,after_json,metadata) values ('opportunity',%s,'fields_updated',%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb)""",(str(opportunity_id),actor_user_id,request_id,idempotency_key,self._json(before),self._json(after),self._json({'fields':list(clean)})))
            return updated

    def transition_opportunity(self, *, opportunity_id: UUID, to_stage: str, expected_version: int, actor_user_id: UUID,
                               closed_reason: str | None = None, request_id: str | None = None,
                               idempotency_key: str | None = None) -> dict[str, Any]:
        allowed={'QUALIFIED','DISCOVERY','EVALUATION','PROPOSAL','NEGOTIATION','WON','LOST'}
        if to_stage not in allowed: raise ValueError('invalid opportunity stage')
        with self._connection_factory() as conn, conn.cursor() as cur:
            replay=self._load_replay(cur,idempotency_key)
            if replay is not None: return replay
            cur.execute("select * from crm.opportunities where opportunity_id=%s for update",(opportunity_id,))
            row=cur.fetchone()
            if row is None: raise CRMNotFoundError(f'opportunity {opportunity_id} not found')
            self._check_version(int(row['version']),expected_version)
            current=str(row['stage'])
            if current in {'WON','LOST'}: raise CRMConflictError('closed opportunities cannot be reopened in CRM MVP')
            if current == to_stage: raise CRMConflictError('opportunity is already in that stage')
            closed_at=datetime.now().astimezone() if to_stage in {'WON','LOST'} else None
            if to_stage == 'LOST' and not str(closed_reason or '').strip(): raise ValueError('closed_reason is required when marking LOST')
            cur.execute("update crm.opportunities set stage=%s,closed_at=%s,closed_reason=%s,version=%s,updated_at=now() where opportunity_id=%s returning *",(to_stage,closed_at,closed_reason if to_stage=='LOST' else None,int(row['version'])+1,opportunity_id))
            updated=dict(cur.fetchone())
            cur.execute("""insert into crm.audit_events(entity_type,entity_id,action,actor_user_id,request_id,idempotency_key,before_json,after_json) values ('opportunity',%s,'stage_changed',%s,%s,%s,%s::jsonb,%s::jsonb)""",(str(opportunity_id),actor_user_id,request_id,idempotency_key,self._json({'stage':current,'version':row['version']}),self._json({'stage':to_stage,'version':updated['version'],'closed_at':updated['closed_at'],'closed_reason':updated['closed_reason']})))
            return updated

    def list_crm_members(self) -> list[dict[str, Any]]:
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select ua.user_id, u.email, ua.role, ua.active
                from crm.user_access ua
                join auth.users u on u.id = ua.user_id
                where ua.active = true
                order by lower(coalesce(u.email, '')), ua.user_id
                """
            )
            return [dict(row) for row in cur.fetchall()]

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
