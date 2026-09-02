from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock, patch

from sentinellayer_growth_engine.tracking_http import make_handler


class FakeServer:
    def __init__(self, *_args, **_kwargs):
        pass


def test_handler_requires_hash_secret() -> None:
    try:
        make_handler(database_url="postgres://db", environment="test", tracking_hash_secret="x")
    except ValueError as exc:
        assert "invalid environment" in str(exc)
    else:
        raise AssertionError("expected invalid environment")


def test_handler_requires_database() -> None:
    try:
        make_handler(database_url="", environment="development", tracking_hash_secret="x")
    except ValueError as exc:
        assert "database_url" in str(exc)
    else:
        raise AssertionError("expected missing database URL")


def test_handler_requires_hash_secret() -> None:
    try:
        make_handler(database_url="postgres://db", environment="development", tracking_hash_secret="")
    except ValueError as exc:
        assert "tracking_hash_secret" in str(exc)
    else:
        raise AssertionError("expected missing hash secret")


def test_handler_class_is_constructible() -> None:
    handler = make_handler(
        database_url="postgres://db",
        environment="development",
        tracking_hash_secret="secret",
    )
    assert handler.server_version == "SentinelLayerTracking/1"


def test_token_shape_is_checked_before_database_lookup() -> None:
    handler = make_handler(
        database_url="postgres://db",
        environment="development",
        tracking_hash_secret="secret",
    )
    instance = object.__new__(handler)
    instance.path = "/t/not-a-token"
    assert instance._token_from_path() is None


def test_token_shape_accepts_opaque_url_safe_token() -> None:
    handler = make_handler(
        database_url="postgres://db",
        environment="development",
        tracking_hash_secret="secret",
    )
    instance = object.__new__(handler)
    instance.path = "/t/AbCdEfGhIjKlMnOpQrStUvWxYz123456"
    assert instance._token_from_path() == "AbCdEfGhIjKlMnOpQrStUvWxYz123456"
