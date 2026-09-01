from __future__ import annotations

from unittest.mock import patch

from sentinellayer_growth_engine import health


def test_health_fails_without_database_url() -> None:
    with patch.dict("os.environ", {}, clear=True):
        assert health.check() == 1


def test_health_does_not_print_secret_on_failure(capsys) -> None:
    secret = "super-secret-value"
    with patch.dict(
        "os.environ",
        {"SL_DATABASE_URL": f"postgresql://user:{secret}@db.invalid/app"},
        clear=True,
    ):
        assert health.check() == 1
    assert secret not in capsys.readouterr().out
