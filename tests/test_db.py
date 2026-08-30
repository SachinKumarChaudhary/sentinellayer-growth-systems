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
        return (False,)

    def __enter__(self) -> "FakeCursor":
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

    def __enter__(self) -> "FakeConnection":
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
