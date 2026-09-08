from datetime import UTC, datetime
from uuid import uuid4

import pytest

from sentinellayer_growth_engine.recommendation_repository import RecommendationRepository
from sentinellayer_growth_engine.recommendations import Recommendation


class FakeCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple]] = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def execute(self, query: str, params: tuple) -> None:
        self.executed.append((query, params))

    def fetchone(self):
        return (uuid4(), "pending", datetime.now(UTC))


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def cursor(self):
        return self.cursor_instance

    def commit(self) -> None:
        pass


def test_persist_writes_pending_operator_recommendation() -> None:
    connection = FakeConnection()
    repository = RecommendationRepository(lambda: connection)  # type: ignore[arg-type]
    recommendation = Recommendation(
        recommendation_type="initial_outreach",
        recommended_channel="email",
        reason="Strong fit and fresh intent.",
        sequence=("email",),
    )
    result = repository.persist(
        company_id=123,
        decision_maker_id=str(uuid4()),
        recommendation=recommendation,
        supporting_signal_ids=(str(uuid4()),),
        draft_message="Draft only",
    )

    query, params = connection.cursor_instance.executed[0]
    assert "growth.recommendations" in query
    assert params[0] == 123
    assert params[2] == "initial_outreach"
    assert params[9] is True
    assert result["status"] == "pending"


def test_invalid_supporting_signal_is_rejected_before_db_write() -> None:
    connection = FakeConnection()
    repository = RecommendationRepository(lambda: connection)  # type: ignore[arg-type]
    recommendation = Recommendation(
        recommendation_type="operator_action",
        recommended_channel="none",
        reason="No automated channel is available.",
        sequence=(),
    )

    with pytest.raises(ValueError):
        repository.persist(
            company_id=123,
            decision_maker_id=None,
            recommendation=recommendation,
            supporting_signal_ids=("not-a-uuid",),
        )

    assert connection.cursor_instance.executed == []


def test_non_approval_recommendation_is_rejected_before_db_write() -> None:
    connection = FakeConnection()
    repository = RecommendationRepository(lambda: connection)  # type: ignore[arg-type]
    recommendation = Recommendation(
        recommendation_type="initial_outreach",
        recommended_channel="email",
        reason="Drafted outreach.",
        sequence=("email",),
        requires_approval=False,
    )

    with pytest.raises(ValueError, match="operator approval"):
        repository.persist(
            company_id=123,
            decision_maker_id=None,
            recommendation=recommendation,
        )

    assert connection.cursor_instance.executed == []
