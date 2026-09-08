from __future__ import annotations

import io
import json
from typing import cast
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from sentinellayer_growth_engine.tinyfish_client import TinyFishClient, TinyFishError


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def test_search_uses_api_key_and_returns_structured_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request: Request, timeout: float) -> _Response:
        captured["url"] = request.full_url
        captured["headers"] = dict(request.headers)
        captured["timeout"] = timeout
        return _Response(
            {
                "results": [
                    {
                        "title": "Leadership",
                        "url": "https://example.com/team",
                        "snippet": "Founder and CEO",
                    }
                ]
            }
        )

    monkeypatch.setattr(
        "sentinellayer_growth_engine.tinyfish_client.urlopen", fake_urlopen
    )
    client = TinyFishClient("secret", timeout_seconds=12)

    results = client.search("example.com CEO", purpose="company enrichment")

    assert results[0].url == "https://example.com/team"
    assert "query=example.com+CEO" in str(captured["url"])
    headers = cast(dict[str, str], captured["headers"])
    assert headers["X-api-key"] == "secret"
    assert captured["timeout"] == 12


def test_fetch_posts_documented_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request: Request, timeout: float) -> _Response:
        captured["method"] = request.method
        captured["url"] = request.full_url
        assert request.data is not None
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _Response(
            {
                "results": [
                    {
                        "url": "https://example.com/team",
                        "final_url": "https://example.com/team",
                        "title": "Leadership",
                        "text": "Founder and CEO",
                        "published_date": "2026-09-01",
                    }
                ]
            }
        )

    monkeypatch.setattr(
        "sentinellayer_growth_engine.tinyfish_client.urlopen", fake_urlopen
    )
    client = TinyFishClient("secret")

    results = client.fetch(
        ["https://example.com/team"],
        purpose="validate leadership evidence",
        include_links=True,
    )

    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.fetch.tinyfish.ai"
    assert captured["body"] == {
        "urls": ["https://example.com/team"],
        "format": "markdown",
        "links": True,
        "image_links": False,
        "page_metadata": False,
        "purpose": "validate leadership evidence",
    }
    assert results[0].text == "Founder and CEO"
    assert results[0].published_date == "2026-09-01"


def test_fetch_enforces_tinyfish_limit() -> None:
    client = TinyFishClient("secret")
    with pytest.raises(ValueError, match="between 1 and 10"):
        client.fetch([])
    with pytest.raises(ValueError, match="between 1 and 10"):
        client.fetch([f"https://example.com/{index}" for index in range(11)])


def test_api_http_errors_do_not_expose_api_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request: Request, timeout: float) -> _Response:
        raise HTTPError(
            request.full_url,
            401,
            "Unauthorized",
            hdrs=None,
            fp=io.BytesIO(b"invalid api key"),
        )

    monkeypatch.setattr(
        "sentinellayer_growth_engine.tinyfish_client.urlopen", fake_urlopen
    )
    client = TinyFishClient("super-secret-key")

    with pytest.raises(TinyFishError) as exc_info:
        client.search("example")

    assert "super-secret-key" not in str(exc_info.value)
    assert "HTTP 401" in str(exc_info.value)
