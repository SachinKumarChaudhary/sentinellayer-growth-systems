from __future__ import annotations

import os
import threading
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

        barrier = threading.Barrier(2)

        def claim(worker_id: str):
            barrier.wait()
            return Database(dsn, worker_id=worker_id).claim_due(batch_size=1, worker_id=worker_id)

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
                select status, claimed_by, attempt_count, claim_lease_until
                from public.sends
                where id = %s
                """,
                (send_id,),
            )
            row = cur.fetchone()

        assert row is not None
        assert row[0] == "claiming"
        assert row[1] in {"ci-worker-a", "ci-worker-b"}
        assert row[2] == 1
        assert row[3] is not None

        # Simulate worker A dying: expire its lease, then prove worker B can reclaim.
        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute(
                "update public.sends set claim_lease_until = now() - interval '1 second' where id = %s",
                (send_id,),
            )

        reclaimed = Database(dsn, worker_id="ci-worker-b").claim_due(
            batch_size=1, worker_id="ci-worker-b"
        )
        assert len(reclaimed) == 1
        assert reclaimed[0].send_id == str(send_id)
        assert reclaimed[0].attempt_count == 2

        # A stale worker must not be able to finalize a claim it no longer owns.
        with pytest.raises(Exception, match="claim ownership lost"):
            Database(dsn, worker_id="ci-worker-a").mark_sent(
                send_id=str(send_id),
                message_id=reclaimed[0].message_id,
                provider_message_id="ci-stale-worker-must-not-win",
            )

        Database(dsn, worker_id="ci-worker-b").mark_failed(
            send_id=str(send_id),
            error="CI lease recovery cleanup",
            retry_at=None,
            transient=False,
        )
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


@pytest.mark.integration
def test_retry_lifecycle_and_stale_completion_fencing() -> None:
    dsn = os.environ.get("SUPABASE_DATABASE_URL")
    if not dsn:
        pytest.skip("SUPABASE_DATABASE_URL is required for integration tests")

    domain_id, mailbox_id, campaign_id, step_id, send_id = (uuid4() for _ in range(5))
    suffix = uuid4().hex
    person_email = f"ci-retry-{suffix}@example.invalid"
    mailbox_email = f"retry-worker-{suffix}@example.invalid"
    person_id = None

    try:
        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute("insert into mail.domains (id, domain_name, purpose, provider, dns_provider, status) values (%s,%s,'outbound','test','test','active')", (domain_id, f"{suffix}.invalid"))
            cur.execute("insert into mail.mailboxes (id, domain_id, email, display_name, provider, credentials_ref, status, health_status, daily_limit) values (%s,%s,%s,'CI Retry','test','ci-test','active','unknown',0)", (mailbox_id, domain_id, mailbox_email))
            cur.execute("insert into public.people (full_name,email,status) values ('CI Retry Test',%s,'NEW') returning id", (person_email,))
            person_id = cur.fetchone()[0]
            cur.execute("insert into public.campaigns (id,name,status,daily_global_limit,timezone) values (%s,'CI Retry','active',0,'UTC')", (campaign_id,))
            cur.execute("insert into public.sequence_steps (id,campaign_id,step_no,delay_days,subject_template,body_template,active) values (%s,%s,1,0,'CI retry','test body',true)", (step_id,campaign_id))
            cur.execute("insert into public.sends (id,person_id,campaign_id,sequence_step_id,mailbox_id,idempotency_key,scheduled_at,status) values (%s,%s,%s,%s,%s,%s,now(),'queued')", (send_id,person_id,campaign_id,step_id,mailbox_id,f"ci-retry-{suffix}"))

        worker = Database(dsn, worker_id="ci-retry-worker")
        claimed = worker.claim_due(batch_size=1, worker_id="ci-retry-worker")
        assert len(claimed) == 1
        assert claimed[0].attempt_count == 1

        from datetime import UTC, datetime, timedelta
        retry_at = datetime.now(UTC) + timedelta(minutes=5)
        worker.mark_failed(send_id=str(send_id), error="temporary provider failure", retry_at=retry_at, transient=True, provider_code="421")

        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute("select status, attempt_count, next_attempt_at, claimed_by from public.sends where id=%s", (send_id,))
            row = cur.fetchone()
        assert row[0] == "queued" and row[1] == 1 and row[2] is not None and row[3] is None

        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute("update public.sends set next_attempt_at=now() where id=%s", (send_id,))
        retried = worker.claim_due(batch_size=1, worker_id="ci-retry-worker")
        assert len(retried) == 1
        assert retried[0].attempt_count == 2

        worker.mark_sent(send_id=str(send_id), message_id=retried[0].message_id, provider_message_id="provider-ci-1")
        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute("select status, attempt_count, claimed_by from public.sends where id=%s", (send_id,))
            row = cur.fetchone()
            cur.execute("select count(*) from public.send_attempts where send_id=%s and attempt_no=2", (send_id,))
            attempts = cur.fetchone()[0]
        assert row[0] == "sent" and row[1] == 2 and row[2] is None and attempts == 1
    finally:
        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute("delete from public.send_attempts where send_id=%s", (send_id,))
            cur.execute("delete from public.sends where id=%s", (send_id,))
            cur.execute("delete from public.sequence_steps where id=%s", (step_id,))
            cur.execute("delete from public.campaigns where id=%s", (campaign_id,))
            if person_id is not None: cur.execute("delete from public.people where id=%s", (person_id,))
            cur.execute("delete from mail.mailboxes where id=%s", (mailbox_id,))
            cur.execute("delete from mail.domains where id=%s", (domain_id,))
