from dataclasses import dataclass

import pytest

from sentinellayer_growth_engine.db import Database


@dataclass
class FakeCursor:
    rows: list[dict]
    query: str | None = None
    params: tuple[object, ...] | None = None

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


@dataclass
class FakeConnection:
    rows: list[dict]

    def cursor(self) -> FakeCursor:
        return FakeCursor(self.rows)

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
            "person_id": 42,
            "campaign_id": "campaign-1",
            "sequence_step_id": "step-1",
            "mailbox_id": "mailbox-1",
            "scheduled_at": "2026-08-30T12:00:00Z",
        }
    ]
    monkeypatch.setattr(db, "connection", lambda: FakeConnection(rows))

    claimed = db.claim_due_sends(5)

    assert len(claimed) == 1
    assert claimed[0].send_id == "send-1"
    assert claimed[0].person_id == 42
