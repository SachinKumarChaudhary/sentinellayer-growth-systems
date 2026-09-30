from __future__ import annotations

from typing import Any, Callable
from uuid import UUID


class CRMReadModelRepository:
    """Read-only CRM projections over canonical growth data and CRM overlays."""

    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self._connection_factory = connection_factory

    def list_accounts(
        self, *, query: str | None = None, state: str | None = None,
        owner_user_id: UUID | None = None, after_id: int | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        where = ["1=1"]
        params: list[Any] = []
        if query:
            where.append("(c.name ilike %s or c.domain ilike %s)")
            like = f"%{query.strip()}%"
            params.extend([like, like])
        if state:
            where.append("coalesce(s.state, 'NEW') = %s")
            params.append(state)
        if owner_user_id:
            where.append("s.owner_user_id = %s")
            params.append(owner_user_id)
        if after_id is not None:
            where.append("c.id > %s")
            params.append(after_id)
        params.append(limit + 1)
        sql = f"""
            select c.id, c.name, c.domain,
                   coalesce(s.state, 'NEW') as state,
                   s.owner_user_id, coalesce(s.version, 0) as version,
                   max(tp.executed_at) as last_activity_at,
                   min(t.due_at) filter (
                     where t.status in ('open','claimed')
                       and t.due_at is not null
                   ) as next_action_at
            from public.companies c
            left join crm.account_state s on s.account_id = c.id
            left join outreach.touchpoints tp on tp.company_id = c.id
            left join sales.tasks t on t.canonical_account_id = c.id
            where {' and '.join(where)}
            group by c.id, c.name, c.domain, s.state, s.owner_user_id, s.version
            order by c.id asc
            limit %s
        """
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            rows = [dict(row) for row in cur.fetchall()]
        has_more = len(rows) > limit
        visible = rows[:limit]
        next_cursor = visible[-1]["id"] if has_more and visible else None
        return {
            "data": visible,
            "meta": {"next_cursor": next_cursor, "has_more": has_more},
        }

    def get_account_360(self, *, account_id: int) -> dict[str, Any]:
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select c.id, c.name, c.domain, c.website, c.company_linkedin,
                       c.country, c.city, c.segment, c.revenue_est, c.visits_est,
                       coalesce(s.state, 'NEW') as state,
                       s.owner_user_id, coalesce(s.version, 0) as version
                from public.companies c
                left join crm.account_state s on s.account_id = c.id
                where c.id = %s
                """,
                (account_id,),
            )
            company = cur.fetchone()
            if company is None:
                raise KeyError(f"account {account_id} not found")
            cur.execute(
                """
                select dm.decision_maker_id, dm.full_name, dm.title,
                       dm.role_family, dm.role_priority, dm.status,
                       coalesce(
                         jsonb_agg(
                           jsonb_build_object(
                             'id', cm.contact_method_id,
                             'channel', cm.channel,
                             'value', cm.value,
                             'normalized_value', cm.normalized_value,
                             'verification_status', cm.verification_status,
                             'confidence', cm.confidence
                           )
                           order by cm.channel, cm.contact_method_id
                         ) filter (where cm.contact_method_id is not null),
                         '[]'::jsonb
                       ) as contact_methods
                from growth.decision_makers dm
                left join growth.decision_maker_contact_methods cm
                  on cm.decision_maker_id = dm.decision_maker_id
                where dm.company_id = %s
                group by dm.decision_maker_id
                order by coalesce(dm.role_priority, 999), dm.full_name asc
                """,
                (account_id,),
            )
            contacts = [dict(row) for row in cur.fetchall()]
            cur.execute(
                """
                select sales_task_id, canonical_person_id, trigger_type, priority,
                       recommended_action, why_now, status, due_at, assigned_to,
                       created_at, updated_at
                from sales.tasks
                where canonical_account_id = %s
                  and status in ('open','claimed')
                order by
                  case when due_at is null then 1 else 0 end,
                  due_at asc, priority asc, created_at asc, sales_task_id asc
                """,
                (account_id,),
            )
            tasks = [dict(row) for row in cur.fetchall()]

            cur.execute(
                """
                select note_id, decision_maker_id, body, author_user_id,
                       created_at, updated_at
                from crm.notes
                where account_id = %s
                order by created_at desc
                """,
                (account_id,),
            )
            notes = [dict(row) for row in cur.fetchall()]
            cur.execute(
                """
                select company_id, fit_score, intent_score, behavior_override,
                       negative_flags, modifiers, priority, scoring_version,
                       scored_at, behavior_stage, behavior_identity,
                       behavior_timestamp, next_review_date
                from intelligence.company_scores
                where company_id = %s
                """,
                (account_id,),
            )
            score = cur.fetchone()

            cur.execute(
                """
                select intent_signal_id, signal_type, signal_date, detected_at,
                       weight, confidence, status, expires_at, evidence_id
                from intelligence.intent_signals
                where company_id = %s
                order by signal_date desc, detected_at desc, intent_signal_id desc
                limit 20
                """,
                (account_id,),
            )
            intent_signals = [dict(row) for row in cur.fetchall()]

            cur.execute(
                """
                select evidence_id, decision_maker_id, claim_type, claim,
                       source_url, source_type, observed_at, event_date, confidence
                from intelligence.evidence
                where company_id = %s
                order by observed_at desc, evidence_id desc
                limit 30
                """,
                (account_id,),
            )
            evidence = [dict(row) for row in cur.fetchall()]

            timeline = self._timeline(cur, account_id)
            return {
                "account": dict(company),
                "intelligence": {
                    "score": dict(score) if score else None,
                    "intent_signals": intent_signals,
                    "evidence": evidence,
                },
                "contacts": contacts,
                "open_tasks": tasks,
                "notes": notes,
                "timeline": timeline,
            }

    @staticmethod
    def _timeline(cur: Any, account_id: int) -> list[dict[str, Any]]:
        cur.execute(
            """
            with events as (
              select
                coalesce(tp.executed_at, tp.scheduled_at, tp.created_at) as occurred_at,
                'activity'::text as event_type,
                tp.touchpoint_id::text as event_id,
                tp.channel,
                tp.touchpoint_type,
                coalesce(tp.metadata->>'summary', tp.touchpoint_type) as summary,
                tp.decision_maker_id::text as person_id
              from outreach.touchpoints tp
              where tp.company_id = %s

              union all
              select
                r.received_at as occurred_at,
                'reply'::text,
                r.reply_id::text,
                null::text,
                'reply',
                left(r.body_text, 500),
                r.person_id
              from conversation.replies r
              where r.canonical_account_id = %s
                 or r.account_id = %s::text

              union all

              select
                h.occurred_at,
                'state_changed'::text,
                h.history_id::text,
                null::text,
                'state_changed',
                concat(coalesce(h.from_state, '∅'), ' → ', h.to_state),
                null::text
              from crm.state_history h
              where h.entity_type = 'account'
                and h.entity_id = %s::text

              union all

              select
                t.created_at,
                'task'::text,
                t.sales_task_id::text,
                null::text,
                t.trigger_type,
                t.recommended_action,
                t.canonical_person_id::text
              from sales.tasks t
              where t.canonical_account_id = %s
            )
            select occurred_at, event_type, event_id, channel,
                   touchpoint_type, summary, person_id
            from events
            order by occurred_at desc nulls last, event_id desc
            limit 200
            """,
            (
                account_id, account_id, str(account_id), str(account_id), account_id
            ),
        )
        return [dict(row) for row in cur.fetchall()]

    def search_accounts(self, *, query: str, limit: int = 25) -> list[dict[str, Any]]:
        if not query.strip():
            raise ValueError("search query must not be empty")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        value = query.strip()
        like = f"%{value}%"
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select c.id, c.name, c.domain,
                       coalesce(s.state, 'NEW') as state,
                       case
                         when lower(c.domain) = lower(%s) then 1
                         when lower(c.name) = lower(%s) then 2
                         when c.domain ilike %s then 3
                         when c.name ilike %s then 4
                         else 5
                       end as match_rank
                from public.companies c
                left join crm.account_state s on s.account_id = c.id
                where lower(c.domain) = lower(%s)
                   or lower(c.name) = lower(%s)
                   or c.domain ilike %s
                   or c.name ilike %s
                order by match_rank, c.id asc
                limit %s
                """,
                (value, value, like, like, value, value, like, like, limit),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_contact_360(self, *, decision_maker_id: UUID) -> dict[str, Any]:
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                """
                select dm.decision_maker_id, dm.company_id, c.name as company_name,
                       c.domain, dm.full_name, dm.title, dm.role_family,
                       dm.role_priority, dm.rationale, dm.status, dm.research_status,
                       dm.confidence, dm.first_seen_at, dm.last_verified_at,
                       dm.created_at, dm.updated_at,
                       coalesce(cs.state, 'NOT_CONTACTED') as state,
                       cs.owner_user_id, coalesce(cs.version, 0) as version
                from growth.decision_makers dm
                join public.companies c on c.id = dm.company_id
                left join crm.contact_state cs on cs.decision_maker_id = dm.decision_maker_id
                where dm.decision_maker_id = %s
                """,
                (decision_maker_id,),
            )
            person = cur.fetchone()
            if person is None:
                raise KeyError(f"contact {decision_maker_id} not found")
            cur.execute(
                """
                select contact_method_id, channel, value, normalized_value,
                       verification_status, confidence, source, first_seen_at, last_verified_at
                from growth.decision_maker_contact_methods
                where decision_maker_id = %s
                order by channel, contact_method_id
                """,
                (decision_maker_id,),
            )
            contact_methods = [dict(row) for row in cur.fetchall()]
            cur.execute(
                """
                select note_id, account_id, body, author_user_id, created_at, updated_at
                from crm.notes
                where decision_maker_id = %s
                order by created_at desc
                """,
                (decision_maker_id,),
            )
            notes = [dict(row) for row in cur.fetchall()]
            cur.execute(
                """
                with events as (
                  select coalesce(tp.executed_at, tp.scheduled_at, tp.created_at) as occurred_at,
                         'activity'::text as event_type, tp.touchpoint_id::text as event_id,
                         tp.channel, tp.touchpoint_type,
                         coalesce(tp.metadata->>'summary', tp.touchpoint_type) as summary
                  from outreach.touchpoints tp
                  where tp.decision_maker_id = %s
                  union all
                  select r.received_at, 'reply'::text, r.reply_id::text, null::text,
                         'reply', left(r.body_text, 500)
                  from conversation.replies r
                  where r.person_id = %s::text or r.canonical_person_id = %s
                  union all
                  select h.occurred_at, 'state_changed'::text, h.history_id::text,
                         null::text, 'state_changed', concat(coalesce(h.from_state,'∅'),' → ',h.to_state)
                  from crm.state_history h
                  where h.entity_type = 'contact' and h.entity_id = %s::text
                  union all
                  select t.created_at, 'task'::text, t.sales_task_id::text,
                         null::text, null::text, t.trigger_type || ': ' || t.recommended_action
                  from sales.tasks t
                  where t.canonical_person_id = %s
                )
                select occurred_at, event_type, event_id, channel, touchpoint_type, summary
                from events
                order by occurred_at desc nulls last, event_id desc
                limit 200
                """,
                (decision_maker_id, str(decision_maker_id), decision_maker_id, str(decision_maker_id), decision_maker_id),
            )
            timeline = [dict(row) for row in cur.fetchall()]
            return {
                "contact": dict(person),
                "contact_methods": contact_methods,
                "notes": notes,
                "timeline": timeline,
            }

    def list_contacts(
        self, *, query: str | None = None, account_id: int | None = None,
        state: str | None = None, channel: str | None = None,
        after_id: UUID | None = None, limit: int = 50,
    ) -> dict[str, Any]:
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        where = ["1=1"]
        params: list[Any] = []
        if query:
            where.append("(dm.full_name ilike %s or dm.title ilike %s)")
            like = f"%{query.strip()}%"
            params.extend([like, like])
        if account_id is not None:
            where.append("dm.company_id = %s")
            params.append(account_id)
        if state:
            where.append("coalesce(cs.state, 'NOT_CONTACTED') = %s")
            params.append(state)
        if channel:
            where.append("exists (select 1 from growth.decision_maker_contact_methods cmx where cmx.decision_maker_id = dm.decision_maker_id and cmx.channel = %s)")
            params.append(channel)
        if after_id:
            where.append("dm.decision_maker_id > %s")
            params.append(after_id)
        params.append(limit + 1)
        sql = f"""
            select dm.decision_maker_id, dm.company_id,
                   c.name as company_name, c.domain,
                   dm.full_name, dm.title, dm.role_family, dm.role_priority,
                   dm.status as research_status,
                   coalesce(cs.state, 'NOT_CONTACTED') as state,
                   cs.owner_user_id, coalesce(cs.version, 0) as version,
                   coalesce(jsonb_agg(distinct jsonb_build_object(
                     'channel', cm.channel,
                     'value', cm.value,
                     'verification_status', cm.verification_status,
                     'confidence', cm.confidence
                   )) filter (where cm.contact_method_id is not null), '[]'::jsonb) as contact_methods
            from growth.decision_makers dm
            join public.companies c on c.id = dm.company_id
            left join crm.contact_state cs on cs.decision_maker_id = dm.decision_maker_id
            left join growth.decision_maker_contact_methods cm
              on cm.decision_maker_id = dm.decision_maker_id
            where {' and '.join(where)}
            group by dm.decision_maker_id, c.name, c.domain,
                     cs.state, cs.owner_user_id, cs.version
            order by dm.decision_maker_id asc
            limit %s
        """
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(sql, params)
            rows = [dict(row) for row in cur.fetchall()]
        has_more = len(rows) > limit
        visible = rows[:limit]
        next_cursor = visible[-1]["decision_maker_id"] if has_more and visible else None
        return {"data": visible, "meta": {"next_cursor": next_cursor, "has_more": has_more}}
    def pipeline_summary(self) -> dict[str, Any]:
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                """
                with states as (
                  select unnest(array[
                    'NEW','QUALIFIED','WORKING','ENGAGED','FOLLOW_UP',
                    'SALES_QUALIFIED','CUSTOMER','NOT_INTERESTED','NURTURE','SUPPRESSED'
                  ]) as state
                ), counts as (
                  select coalesce(s.state, 'NEW') as state, count(*)::bigint as account_count
                  from public.companies c
                  left join crm.account_state s on s.account_id = c.id
                  group by coalesce(s.state, 'NEW')
                )
                select states.state, coalesce(counts.account_count, 0) as account_count
                from states
                left join counts on counts.state = states.state
                order by array_position(array[
                  'NEW','QUALIFIED','WORKING','ENGAGED','FOLLOW_UP',
                  'SALES_QUALIFIED','CUSTOMER','NOT_INTERESTED','NURTURE','SUPPRESSED'
                ], states.state)
                """
            )
            rows = [dict(row) for row in cur.fetchall()]
        return {"data": rows, "meta": {"total_accounts": sum(int(r["account_count"]) for r in rows)}}
