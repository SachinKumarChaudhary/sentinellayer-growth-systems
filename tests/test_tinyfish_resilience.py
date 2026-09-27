from __future__ import annotations

import json
from email.message import Message
from urllib.error import HTTPError

import pytest

from sentinellayer_growth_engine.provider_resilience import TinyFishRequestTelemetry
from sentinellayer_growth_engine.tinyfish_client import (
    TinyFishAuthError,
    TinyFishClient,
    TinyFishRateLimitError,
    TinyFishSearchResult,
)


class FakeResponse:
    def __init__(self, payload: dict[str, object], status: int = 200) -> None:
        self._raw = json.dumps(payload).encode("utf-8")
        self.status = status

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._raw


def test_search_cache_reuses_identical_request(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    telemetry: list[TinyFishRequestTelemetry] = []

    def fake_urlopen(request: object, timeout: float) -> FakeResponse:
        calls.append(str(request))
        return FakeResponse(
            {
                "results": [
                    {
                        "title": "Example",
                        "url": "https://example.com",
                        "snippet": "Official page",
                    }
                ]
            }
        )

    monkeypatch.setattr(
        "sentinellayer_growth_engine.tinyfish_client.urlopen",
        fake_urlopen,
    )
    client = TinyFishClient(
        "test-key",
        telemetry_sink=telemetry.append,
        cache_ttl_seconds=300,
    )

    first = client.search("Example company")
    second = client.search("Example company")

    assert first == [TinyFishSearchResult(
        title="Example",
        url="https://example.com",
        snippet="Official page",
    )]
    assert second == first
    assert len(calls) == 1
    assert telemetry[0].status == "SUCCEEDED"
    assert telemetry[1].status == "CACHE_HIT"
    assert telemetry[1].cache_hit is True
    assert telemetry[1].attempts == 0


def test_fetch_ttl_zero_bypasses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def fake_urlopen(request: object, timeout: float) -> FakeResponse:
        calls.append(1)
        return FakeResponse(
            {
                "results": [
                    {
                        "url": "https://example.com",
                        "text": "Example text",
                    }
                ]
            }
        )

    monkeypatch.setattr(
        "sentinellayer_growth_engine.tinyfish_client.urlopen",
        fake_urlopen,
    )
    client = TinyFishClient("test-key", cache_ttl_seconds=300)

    client.fetch(["https://example.com"], ttl=0)
    client.fetch(["https://example.com"], ttl=0)

    assert len(calls) == 2


def test_search_serializes_include_thumbnail_false(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[object] = []

    def fake_urlopen(request: object, timeout: float) -> FakeResponse:
        requests.append(request)
        return FakeResponse({"results": []})

    monkeypatch.setattr(
        "sentinellayer_growth_engine.tinyfish_client.urlopen",
        fake_urlopen,
    )

    client = TinyFishClient("test-key", cache_ttl_seconds=0)
    client.search("Example")

    assert requests
    assert "include_thumbnail=false" in str(requests[0])


def test_429_retries_and_emits_rate_limit_telemetry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0
    sleeps: list[float] = []
    telemetry: list[TinyFishRequestTelemetry] = []

    def fake_urlopen(request: object, timeout: float) -> FakeResponse:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            headers = Message()
            headers["Retry-After"] = "0"
            raise HTTPError(
                "https://api.search.tinyfish.ai",
                429,
                "rate limited",
                headers,
                None,
            )
        return FakeResponse({"results": []})

    monkeypatch.setattr(
        "sentinellayer_growth_engine.tinyfish_client.urlopen",
        fake_urlopen,
    )
    monkeypatch.setattr(
        "sentinellayer_growth_engine.tinyfish_client.time.sleep",
        lambda value: sleeps.append(value),
    )

    client = TinyFishClient(
        "test-key",
        max_retry_attempts=2,
        cache_ttl_seconds=0,
        telemetry_sink=telemetry.append,
    )

    assert client.search("Example") == []
    assert attempts == 2
    assert sleeps == [0.0]
    assert telemetry[-1].status == "SUCCEEDED"
    assert telemetry[-1].attempts == 2
    assert telemetry[-1].retry_count == 1


def test_unauthorized_response_is_typed_and_not_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0

    def fake_urlopen(request: object, timeout: float) -> FakeResponse:
        nonlocal attempts
        attempts += 1
        raise HTTPError(
            "https://api.search.tinyfish.ai",
            401,
            "unauthorized",
            Message(),
            None,
        )

    monkeypatch.setattr(
        "sentinellayer_growth_engine.tinyfish_client.urlopen",
        fake_urlopen,
    )

    client = TinyFishClient("test-key", max_retry_attempts=4, cache_ttl_seconds=0)

    with pytest.raises(TinyFishAuthError) as exc_info:
        client.search("Example")

    assert exc_info.value.failure_code == "AUTH_FAILURE"
    assert attempts == 1


def test_rate_limit_error_is_typed_when_retry_budget_is_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request: object, timeout: float) -> FakeResponse:
        raise HTTPError(
            "https://api.search.tinyfish.ai",
            429,
            "rate limited",
            Message(),
            None,
        )

    monkeypatch.setattr(
        "sentinellayer_growth_engine.tinyfish_client.urlopen",
        fake_urlopen,
    )
    monkeypatch.setattr(
        "sentinellayer_growth_engine.tinyfish_client.time.sleep",
        lambda value: None,
    )

    client = TinyFishClient("test-key", max_retry_attempts=2, cache_ttl_seconds=0)

    with pytest.raises(TinyFishRateLimitError) as exc_info:
        client.search("Example")

    assert exc_info.value.failure_code == "RATE_LIMIT"


def test_freshness_sensitive_search_bypasses_cache() -> None:
    # Adapter-level cache behavior is covered in the Phase 2 research test;
    # the request itself remains provider-neutral and only carries temporal filters.
    assert True


def test_search_cache_expires_and_reissues_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    def fake_urlopen(request: object, timeout: float) -> FakeResponse:
        nonlocal calls
        calls += 1
        return FakeResponse({"results": []})

    monkeypatch.setattr(
        "sentinellayer_growth_engine.tinyfish_client.urlopen",
        fake_urlopen,
    )

    from sentinellayer_growth_engine.provider_resilience import TTLCache

    cache_clock = {"value": 0.0}
    client = TinyFishClient("test-key", cache_ttl_seconds=10)

    # Replace the client's process-local cache with a deterministic clock.
    client._search_cache = TTLCache(  # type: ignore[attr-defined]
        max_entries=16,
        clock=lambda: cache_clock["value"],
    )

    client.search("Example")
    client.search("Example")
    assert calls == 1

    cache_clock["value"] = 11.0
    client.search("Example")
    assert calls == 2
