from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
import pytest

from sentinellayer_growth_engine.db import Database


@pytest.mark.integration
def test_two_workers_cannot_claim_same_send() -> None:
    dsn = os.environ.get("SUPABASE_DATABASE_URL")
    if not dsn:
        pytest.skip("SUPABASE_DATABASE_URL is required for integration tests")

    domain_id = uuid4()
    mailbox_id = uuid4()
    campaign_id = uuid4()
    step_id = uuid4()
    send_id = uuid4()
    suffix = uuid4().hex
    person_email = f"ci-{suffix}@example.invalid"
    mailbox_email = f"worker-{suffix}@example.invalid"
    idempotency_key = f"ci-concurrency-{suffix}"

    person_id: int | None = None
    try:
        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into mail.domains
                    (id, domain_name, purpose, provider, dns_provider, status)
                values (%s, %s, 'outbound', 'test', 'test', 'active')
                """,
                (domain_id, f"{suffix}.invalid"),
            )
            cur.execute(
                """
                insert into mail.mailboxes
                    (id, domain_id, email, display_name, provider,
                     credentials_ref, status, health_status, daily_limit)
                values (%s, %s, %s, 'CI Worker', 'test', 'ci-test',
                        'active', 'unknown', 0)
                """,
                (mailbox_id, domain_id, mailbox_email),
            )
            cur.execute(
                """
                insert into public.people (full_name, email, status)
                values ('CI Concurrency Test', %s, 'NEW')
                returning id
                """,
                (person_email,),
            )
            person_id = cur.fetchone()[0]
            cur.execute(
                """
                insert into public.campaigns
                    (id, name, status, daily_global_limit, timezone)
                values (%s, 'CI Concurrency Test', 'active', 0, 'UTC')
                """,
                (campaign_id,),
            )
            cur.execute(
                """
                insert into public.sequence_steps
                    (id, campaign_id, step_no, delay_days,
                     subject_template, body_template, active)
                values (%s, %s, 1, 0, 'CI concurrency', 'test body', true)
                """,
                (step_id, campaign_id),
            )
            cur.execute(
                """
                insert into public.sends
                    (id, person_id, campaign_id, sequence_step_id, mailbox_id,
                     idempotency_key, scheduled_at, status)
                values (%s, %s, %s, %s, %s, %s, now(), 'queued')
                """,
                (
                    send_id,
                    person_id,
                    campaign_id,
                    step_id,
                    mailbox_id,
                    idempotency_key,
                ),
            )

        barrier = __import__("threading").Barrier(2)

        def claim(worker_id: str):
            barrier.wait()
            return Database(dsn).claim_due(batch_size=1, worker_id=worker_id)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(claim, "ci-worker-a"),
                executor.submit(claim, "ci-worker-b"),
            ]
            results = [future.result() for future in futures]

        claimed = [send for batch in results for send in batch]
        assert len(claimed) == 1
        assert claimed[0].send_id == str(send_id)
        assert claimed[0].attempt_count == 1

        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute(
                """
                select status, claimed_by, attempt_count
                from public.sends
                where id = %s
                """,
                (send_id,),
            )
            row = cur.fetchone()

        assert row == ("claiming", claimed[0] and row[1], 1)
    finally:
        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute("delete from public.sends where id = %s", (send_id,))
            cur.execute(
                "delete from public.sequence_steps where id = %s",
                (step_id,),
            )
            cur.execute(
                "delete from public.campaigns where id = %s",
                (campaign_id,),
            )
            if person_id is not None:
                cur.execute(
                    "delete from public.people where id = %s",
                    (person_id,),
                )
            cur.execute(
                "delete from mail.mailboxes where id = %s",
                (mailbox_id,),
            )
            cur.execute(
                "delete from mail.domains where id = %s",
                (domain_id,),
            )
