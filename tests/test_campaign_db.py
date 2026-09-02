from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from sentinellayer_growth_engine.campaign_db import CampaignDatabase


def make_db():
    return CampaignDatabase("postgresql://example", "worker-a")


def fake_connection(row=None):
    conn = MagicMock()
    cur = MagicMock()
    cur.fetchone.return_value = row
    conn.cursor.return_value.__enter__.return_value = cur
    conn.__enter__.return_value = conn
    return conn, cur


def test_claim_calls_atomic_database_function():
    row = {"enrollment_id": "11111111-1111-4111-8111-111111111111", "step_no": 1}
    conn, cur = fake_connection(row)
    with patch.object(CampaignDatabase, "_connection", return_value=conn):
        assert make_db().claim_step(row["enrollment_id"]) == row
    cur.execute.assert_called_once_with(
        "select * from public.claim_campaign_step(%s, %s, %s)",
        (row["enrollment_id"], "worker-a", 300),
    )


def test_release_returns_database_result():
    enrollment = "11111111-1111-4111-8111-111111111111"
    token = "22222222-2222-4222-8222-222222222222"
    conn, cur = fake_connection((True,))
    with patch.object(CampaignDatabase, "_connection", return_value=conn):
        assert make_db().release_step(enrollment, token) is True


def test_complete_requires_timezone_aware_time():
    with pytest.raises(ValueError, match="timezone-aware"):
        make_db().complete_step(
            "11111111-1111-4111-8111-111111111111",
            "22222222-2222-4222-8222-222222222222",
            1,
            datetime(2026, 9, 2),
        )


def test_complete_calls_database_function():
    enrollment = "11111111-1111-4111-8111-111111111111"
    token = "22222222-2222-4222-8222-222222222222"
    when = datetime(2026, 9, 3, 12, tzinfo=UTC)
    conn, cur = fake_connection((True,))
    with patch.object(CampaignDatabase, "_connection", return_value=conn):
        assert make_db().complete_step(enrollment, token, 1, when) is True
    cur.execute.assert_called_once_with(
        "select public.complete_campaign_step_claim(%s, %s, %s, %s)",
        (enrollment, token, 1, when),
    )
