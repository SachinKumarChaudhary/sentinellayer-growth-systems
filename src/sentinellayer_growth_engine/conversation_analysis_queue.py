from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .conversation_analyzer import ConversationAnalyzer


@dataclass(frozen=True)
class AnalysisJob:
    analysis_id: str
    reply_id: str
    subject: str
    body_text: str
    conversation_context: str
    attempt_count: int


class ConversationAnalysisQueue:
    """Durable queue for semantic analysis; provider failures never lose the reply."""

    def __init__(self, dsn: str, worker_id: str = "conversation-analyzer") -> None:
        if not dsn.strip():
            raise ValueError("dsn must not be empty")
        if not worker_id.strip():
            raise ValueError("worker_id must not be empty")
        self._dsn = dsn
        self._worker_id = worker_id

    def connection(self) -> psycopg.Connection[Any]:
        return psycopg.connect(self._dsn, row_factory=dict_row)

    def enqueue(self, reply_id: str) -> str:
        if not reply_id.strip():
            raise ValueError("reply_id must not be empty")
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into conversation.analysis_jobs (reply_id)
                values (%s)
                on conflict (reply_id) do nothing
                returning analysis_id
                """,
                (reply_id,),
            )
            row = cur.fetchone()
            if row is not None:
                return str(row["analysis_id"])
            cur.execute(
                "select analysis_id from conversation.analysis_jobs where reply_id=%s",
                (reply_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("analysis job dedupe lookup returned no row")
            return str(row["analysis_id"])

    def claim(self, *, batch_size: int = 10, lease_seconds: int = 120) -> list[AnalysisJob]:
        if batch_size < 1 or batch_size > 100:
            raise ValueError("batch_size must be between 1 and 100")
        if lease_seconds < 10 or lease_seconds > 3600:
            raise ValueError("lease_seconds must be between 10 and 3600")
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                with candidates as (
                    select analysis_id
                    from conversation.analysis_jobs
                    where status='pending'
                       or (status='processing' and lease_until < now())
                    order by created_at
                    for update skip locked
                    limit %s
                )
                update conversation.analysis_jobs j
                set status='processing',
                    attempt_count=j.attempt_count + 1,
                    lease_owner=%s,
                    lease_until=now() + (%s * interval '1 second'),
                    updated_at=now()
                from candidates c
                where j.analysis_id=c.analysis_id
                returning j.analysis_id, j.reply_id, j.attempt_count
                """,
                (batch_size, self._worker_id, lease_seconds),
            )
            claimed = cur.fetchall()
            jobs: list[AnalysisJob] = []
            for row in claimed:
                cur.execute(
                    """
                    select j.analysis_id, j.reply_id, r.subject, r.body_text,
                           t.thread_key, t.state, r.classification
                    from conversation.analysis_jobs j
                    join conversation.replies r on r.reply_id=j.reply_id
                    join conversation.threads t on t.conversation_id=r.conversation_id
                    where j.analysis_id=%s
                    """,
                    (row["analysis_id"],),
                )
                detail = cur.fetchone()
                if detail is None:
                    raise RuntimeError("claimed analysis job reply disappeared")
                context = (
                    f"thread_key={detail['thread_key']}\n"
                    f"conversation_state={detail['state']}\n"
                    f"deterministic_classification={detail['classification']}"
                )
                jobs.append(
                    AnalysisJob(
                        analysis_id=str(detail["analysis_id"]),
                        reply_id=str(detail["reply_id"]),
                        subject=str(detail["subject"]),
                        body_text=str(detail["body_text"]),
                        conversation_context=context,
                        attempt_count=int(row["attempt_count"]),
                    )
                )
            return jobs

    def complete(
        self,
        *,
        analysis_id: str,
        analysis: dict[str, Any],
        provider: str,
        model: str,
    ) -> None:
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                update conversation.analysis_jobs
                set status='completed', analysis=%s::jsonb, provider=%s, model=%s,
                    lease_owner=null, lease_until=null, error=null,
                    completed_at=now(), updated_at=now()
                where analysis_id=%s and status='processing' and lease_owner=%s
                """,
                (json.dumps(analysis), provider, model, analysis_id, self._worker_id),
            )
            if cur.rowcount != 1:
                raise RuntimeError("analysis completion lost worker lease")

    def fail(self, *, analysis_id: str, error: str) -> None:
        with self.connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                update conversation.analysis_jobs
                set status=case when attempt_count >= 5 then 'failed' else 'pending' end,
                    lease_owner=null, lease_until=null,
                    error=%s, updated_at=now()
                where analysis_id=%s and status='processing' and lease_owner=%s
                """,
                (error[:4000], analysis_id, self._worker_id),
            )
            if cur.rowcount != 1:
                raise RuntimeError("analysis failure update lost worker lease")


class ConversationAnalysisWorker:
    """Run bounded provider analysis against leased durable jobs."""

    def __init__(self, queue: ConversationAnalysisQueue, analyzer: ConversationAnalyzer) -> None:
        self._queue = queue
        self._analyzer = analyzer

    def run_once(self, *, batch_size: int = 10) -> int:
        jobs = self._queue.claim(batch_size=batch_size)
        processed = 0
        for job in jobs:
            try:
                analysis = self._analyzer.analyze(
                    subject=job.subject,
                    body_text=job.body_text,
                    conversation_context=job.conversation_context,
                )
                self._queue.complete(
                    analysis_id=job.analysis_id,
                    analysis=analysis,
                    provider="groq",
                    model=getattr(self._analyzer, "model", "unknown"),
                )
            except Exception as exc:
                self._queue.fail(analysis_id=job.analysis_id, error=str(exc))
            processed += 1
        return processed
