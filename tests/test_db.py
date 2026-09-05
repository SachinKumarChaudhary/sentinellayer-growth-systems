from datetime import UTC, datetime
from typing import Self

import pytest

from sentinellayer_growth_engine.db import Database


class FakeCursor:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.query: str | None = None
        self.params: tuple[object, ...] | None = None

    def execute(self, query: str, params: tuple[object, ...] = ()) -> None:
        self.query = query
        self.params = params

    def fetchall(self) -> list[dict]:
        return self.rows

    def fetchone(self) -> object:
        if self.query and "returning sales_task_id" in self.query.lower():
            return {
                "sales_task_id": "11111111-1111-4111-8111-111111111111",
                "account_id": "account-1",
                "person_id": "person-1",
                "trigger_type": "interested",
                "priority": "P1",
                "recommended_action": "human_follow_up",
                "status": "open",
            }
        return (False,)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class FakeConnection:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.last_cursor: FakeCursor | None = None

    def cursor(self) -> FakeCursor:
        self.last_cursor = FakeCursor(self.rows)
        return self.last_cursor

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_claim_rejects_invalid_batch_size() -> None:
    db = Database("postgresql://invalid")
    with pytest.raises(ValueError, match="batch_size"):
        db.claim_due_sends(0)


def test_claim_maps_database_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    db = Database("postgresql://invalid")
    rows = [
        {
            "send_id": "send-1",
            "sender": "sender@sentinellayer.invalid",
            "recipient": "recipient@example.invalid",
            "subject": "Test",
            "body_text": "Hello",
            "message_id": "<send-1@sentinellayer.invalid>",
            "attempt_count": 2,
        }
    ]
    connection = FakeConnection(rows)
    monkeypatch.setattr(db, "connection", lambda: connection)

    claimed = db.claim_due(batch_size=5, worker_id="worker-test")

    assert len(claimed) == 1
    assert claimed[0].send_id == "send-1"
    assert claimed[0].attempt_count == 2
    assert connection.last_cursor is not None
    assert connection.last_cursor.params == (5, "worker-test")


def test_upsert_open_sales_task_uses_idempotent_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    db = Database("postgresql://invalid")
    connection = FakeConnection([{
        "sales_task_id": "11111111-1111-4111-8111-111111111111",
        "account_id": "account-1",
        "person_id": "person-1",
        "trigger_type": "interested",
        "priority": "P1",
        "recommended_action": "human_follow_up",
        "status": "open",
    }])
    monkeypatch.setattr(db, "connection", lambda: connection)
    handoff = {
        "sales_task_id": "11111111-1111-4111-8111-111111111111",
        "account_id": "account-1",
        "person_id": "person-1",
        "trigger_type": "interested",
        "priority": "P1",
        "recommended_action": "human_follow_up",
        "why_now": ["positive reply"],
    }
    out = db.upsert_open_sales_task(handoff)
    assert out["status"] == "open"
    assert connection.last_cursor is not None
    assert "on conflict (account_id, person_id, trigger_type)" in (connection.last_cursor.query or "")


def test_upsert_open_task_aliases_sales_store(monkeypatch: pytest.MonkeyPatch) -> None:
    db = Database("postgresql://invalid")
    sentinel = {"sales_task_id": "x"}
    monkeypatch.setattr(db, "upsert_open_sales_task", lambda handoff: sentinel)
    assert db.upsert_open_task({"sales_task_id": "x"}) is sentinel


def test_persist_handoff_dedupes_provider_message_id(monkeypatch: pytest.MonkeyPatch) -> None:
    db = Database("postgresql://invalid")

    class ConversationCursor(FakeCursor):
        def execute(self, query: str, params=()):
            super().execute(query, params)

        def fetchone(self):
            query = (self.query or "").lower()
            if "conversation.threads" in query:
                return {"conversation_id": "11111111-1111-4111-8111-111111111111"}
            if "insert into conversation.replies" in query:
                return None
            if "select reply_id" in query:
                return {"reply_id": "22222222-2222-4222-8222-222222222222"}
            return super().fetchone()

    class ConversationConnection(FakeConnection):
        def cursor(self):
            self.last_cursor = ConversationCursor(self.rows)
            return self.last_cursor

    connection = ConversationConnection([])
    monkeypatch.setattr(db, "connection", lambda: connection)
    out = db.persist_handoff(
        handoff={
            "conversation_id": "11111111-1111-4111-8111-111111111111",
            "reply_id": "22222222-2222-4222-8222-222222222222",
            "account_id": "account-1",
            "person_id": "person-1",
            "classification": "interested",
            "source_send_id": None,
        },
        sender_email="buyer@example.com",
        subject="Re: hello",
        body_text="Interested",
        provider_message_id="<provider-1@example.com>",
        thread_key="<thread-1>",
        received_at=datetime(2026, 9, 5, 12, tzinfo=UTC),
    )
    assert out["status"] == "duplicate"
    assert out["reply_id"] == "22222222-2222-4222-8222-222222222222"
