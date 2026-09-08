from __future__ import annotations

import json
from typing import Any
from unittest.mock import Mock

import pytest

from sentinellayer_growth_engine.tinyfish_client import TinyFishClient, TinyFishError


def _mock_response(payload: dict[str, object]) -> Mock:
    response = Mock()
    response.__enter__.return_value = response
    response.read.return_value = json.dumps(payload).encode("utf-8")
    return response


def test_search_uses_api_key_and_returns_structured_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = _mock_response(
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
    captured: dict[str, Any] = {}

    def fake_urlopen(request: Any, timeout: float) -> Mock:
        captured["request"] = request
        captured["timeout"] = timeout
        return response

    monkeypatch.setattr(
        "sentinellayer_growth_engine.tinyfish_client.urlopen", fake_urlopen
    )
    client = TinyFishClient("secret", timeout_seconds=12)

    results = client.search("example.com CEO", purpose="company enrichment")

    request = captured["request"]
    assert request.get_header("X-api-key") == "secret"
    assert "query=example.com+CEO" in request.full_url
    assert captured["timeout"] == 12
    assert results[0].url == "https://example.com/team"


def test_fetch_posts_documented_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _mock_response(
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
    captured: dict[str, Any] = {}

    def fake_urlopen(request: Any, timeout: float) -> Mock:
        captured["request"] = request
        return response

    monkeypatch.setattr(
        "sentinellayer_growth_engine.tinyfish_client.urlopen", fake_urlopen
    )
    client = TinyFishClient("secret")

    results = client.fetch(
        ["https://example.com/team"],
        purpose="validate leadership evidence",
        include_links=True,
    )

    request = captured["request"]
    assert request.full_url == "https://api.fetch.tinyfish.ai"
    assert request.method == "POST"
    assert json.loads(request.data.decode("utf-8")) == {
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


def test_api_errors_do_not_expose_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request: Any, timeout: float) -> None:
        raise RuntimeError("fake transport failure")

    monkeypatch.setattr(
        "sentinellayer_growth_engine.tinyfish_client.urlopen", fake_urlopen
    )
    client = TinyFishClient("super-secret-key")

    with pytest.raises(RuntimeError, match="fake transport failure"):
        client.search("example")
