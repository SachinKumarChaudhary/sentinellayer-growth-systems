from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .provider_resilience import (
    TTLCache,
    TelemetrySink,
    TinyFishRequestTelemetry,
    request_fingerprint,
    utc_now,
)
from .tinyfish_rate_limit import TinyFishQuotaExceeded, TinyFishRateLimiter


class TinyFishError(RuntimeError):
    """Base error for TinyFish provider-boundary failures."""

    failure_code = "PROVIDER_ERROR"
    retryable = False

    def __init__(
        self,
        message: str,
        *,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.http_status = http_status


class TinyFishAuthError(TinyFishError):
    failure_code = "AUTH_FAILURE"


class TinyFishRateLimitError(TinyFishError):
    failure_code = "RATE_LIMIT"
    retryable = True


class TinyFishTimeoutError(TinyFishError):
    failure_code = "TIMEOUT"
    retryable = True


class TinyFishNetworkError(TinyFishError):
    failure_code = "NETWORK_ERROR"
    retryable = True


class TinyFishProviderError(TinyFishError):
    failure_code = "PROVIDER_5XX"
    retryable = True


class TinyFishInvalidRequestError(TinyFishError):
    failure_code = "INVALID_REQUEST"


class TinyFishPolicyBlockError(TinyFishError):
    failure_code = "POLICY_BLOCK"


class TinyFishMalformedResultError(TinyFishError):
    failure_code = "MALFORMED_RESULT"


@dataclass(frozen=True)
class TinyFishSearchResult:
    title: str
    url: str
    snippet: str


@dataclass(frozen=True)
class TinyFishFetchResult:
    url: str
    text: str
    title: str | None = None
    final_url: str | None = None
    published_date: str | None = None


class TinyFishClient:
    """Read-only TinyFish Search/Fetch adapter with bounded cache and telemetry."""

    def __init__(
        self,
        api_key: str,
        *,
        search_url: str = "https://api.search.tinyfish.ai",
        fetch_url: str = "https://api.fetch.tinyfish.ai",
        timeout_seconds: float = 30.0,
        rate_limiter: TinyFishRateLimiter | None = None,
        max_retry_attempts: int = 4,
        cache_ttl_seconds: float | None = None,
        max_cache_entries: int = 1024,
        telemetry_sink: TelemetrySink | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("TinyFish API key is required")
        if timeout_seconds <= 0:
            raise ValueError("TinyFish timeout must be positive")
        if max_retry_attempts <= 0:
            raise ValueError("TinyFish max_retry_attempts must be positive")
        effective_cache_ttl = (
            float(os.getenv("PROVIDER_CACHE_TTL_SECONDS", "300"))
            if cache_ttl_seconds is None
            else cache_ttl_seconds
        )
        if effective_cache_ttl < 0:
            raise ValueError("TinyFish cache_ttl_seconds cannot be negative")

        self._api_key = api_key
        self._search_url = search_url
        self._fetch_url = fetch_url
        self._timeout_seconds = timeout_seconds
        self._rate_limiter = rate_limiter or TinyFishRateLimiter()
        self._max_retry_attempts = max_retry_attempts
        self._cache_ttl_seconds = effective_cache_ttl
        self._search_cache: TTLCache[dict[str, Any]] = TTLCache(
            max_entries=max_cache_entries
        )
        self._fetch_cache: TTLCache[dict[str, Any]] = TTLCache(
            max_entries=max_cache_entries
        )
        self._telemetry_sink = telemetry_sink

    def search(
        self,
        query: str,
        *,
        purpose: str | None = None,
        location: str | None = None,
        language: str | None = None,
        include_domains: tuple[str, ...] = (),
        exclude_domains: tuple[str, ...] = (),
        recency_minutes: int | None = None,
        after_date: str | None = None,
        before_date: str | None = None,
        domain_type: str | None = None,
        page: int = 0,
        include_thumbnail: bool = False,
        ttl: float | None = None,
    ) -> list[TinyFishSearchResult]:
        """Run one public-web search and return structured results."""
        if not query.strip():
            raise ValueError("TinyFish search query must not be empty")
        if recency_minutes is not None and (after_date is not None or before_date is not None):
            raise ValueError("recency_minutes cannot be combined with absolute date bounds")
        if recency_minutes is not None and not 1 <= recency_minutes <= 5_256_000:
            raise ValueError("recency_minutes must be between 1 and 5_256_000")
        if after_date and before_date and after_date > before_date:
            raise ValueError("after_date must be on or before before_date")
        if page < 0 or page > 10:
            raise ValueError("TinyFish Search page must be between 0 and 10")
        effective_ttl = self._effective_ttl(ttl)

        params: dict[str, str] = {
            "query": query,
            "page": str(page),
            "include_thumbnail": str(include_thumbnail).lower(),
        }
        if purpose:
            params["purpose"] = purpose
        if location:
            params["location"] = location
        if language:
            params["language"] = language
        if include_domains:
            params["include_domains"] = ",".join(include_domains)
        if exclude_domains:
            params["exclude_domains"] = ",".join(exclude_domains)
        if recency_minutes is not None:
            params["recency_minutes"] = str(recency_minutes)
        if after_date:
            params["after_date"] = after_date
        if before_date:
            params["before_date"] = before_date
        if domain_type:
            if domain_type == "research_paper":
                raise ValueError("research_paper is outside normal Phase 2 entity research")
            if domain_type not in {"web", "news"}:
                raise ValueError("TinyFish Search domain_type must be web or news")
            params["domain_type"] = domain_type

        payload = self._request_json(
            "search",
            "GET",
            f"{self._search_url}?{urlencode(params)}",
            quota_units=1,
            cache=self._search_cache,
            ttl=effective_ttl,
        )
        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            raise TinyFishMalformedResultError(
                "TinyFish Search returned an invalid results payload"
            )
        results: list[TinyFishSearchResult] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            url = item.get("url")
            snippet = item.get("snippet", "")
            if (
                isinstance(title, str)
                and isinstance(url, str)
                and isinstance(snippet, str)
            ):
                results.append(
                    TinyFishSearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                    )
                )
        return results

    def fetch(
        self,
        urls: list[str],
        *,
        purpose: str | None = None,
        format: str = "markdown",
        include_links: bool = False,
        include_image_links: bool = False,
        include_page_metadata: bool = False,
        ttl: float | None = None,
    ) -> list[TinyFishFetchResult]:
        """Fetch up to ten known public URLs using TinyFish's read-only API."""
        if not 1 <= len(urls) <= 10:
            raise ValueError("TinyFish Fetch accepts between 1 and 10 URLs")
        if any(not url.startswith(("http://", "https://")) for url in urls):
            raise ValueError("TinyFish Fetch URLs must use http or https")
        if format not in {"markdown", "html", "json"}:
            raise ValueError("TinyFish Fetch format must be markdown, html, or json")
        effective_ttl = self._effective_ttl(ttl)

        body: dict[str, Any] = {
            "urls": urls,
            "format": format,
            "links": include_links,
            "image_links": include_image_links,
            "page_metadata": include_page_metadata,
        }
        if purpose:
            body["purpose"] = purpose
        payload = self._request_json(
            "fetch",
            "POST",
            self._fetch_url,
            body,
            quota_units=len(urls),
            cache=self._fetch_cache,
            ttl=effective_ttl,
        )
        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            raise TinyFishMalformedResultError(
                "TinyFish Fetch returned an invalid results payload"
            )
        results: list[TinyFishFetchResult] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            url = item.get("url")
            text = item.get("text", "")
            if not isinstance(url, str) or not isinstance(text, str):
                continue
            results.append(
                TinyFishFetchResult(
                    url=url,
                    text=text,
                    title=item.get("title") if isinstance(item.get("title"), str) else None,
                    final_url=(
                        item.get("final_url")
                        if isinstance(item.get("final_url"), str)
                        else None
                    ),
                    published_date=(
                        item.get("published_date")
                        if isinstance(item.get("published_date"), str)
                        else None
                    ),
                )
            )
        return results

    def _effective_ttl(self, ttl: float | None) -> float:
        value = self._cache_ttl_seconds if ttl is None else ttl
        if value < 0:
            raise ValueError("TinyFish ttl cannot be negative")
        return value

    def _request_json(
        self,
        operation: str,
        method: str,
        url: str,
        body: dict[str, Any] | None = None,
        *,
        quota_units: int = 1,
        cache: TTLCache[dict[str, Any]] | None = None,
        ttl: float = 0,
    ) -> dict[str, Any]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        fingerprint = request_fingerprint(method=method, url=url, body=body)
        started_at = utc_now()
        cache_hit = False

        if cache is not None and ttl > 0:
            cached = cache.get(fingerprint)
            if cached is not None:
                cache_hit = True
                self._emit_telemetry(
                    operation=operation,
                    request_fingerprint=fingerprint,
                    started_at=started_at,
                    quota_units=quota_units,
                    attempts=0,
                    retry_count=0,
                    cache_hit=True,
                    status="CACHE_HIT",
                )
                return cached

        headers = {"X-API-Key": self._api_key, "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"

        last_error: TinyFishError | None = None
        for attempt in range(self._max_retry_attempts):
            try:
                if operation == "search":
                    self._rate_limiter.acquire_search()
                else:
                    self._rate_limiter.acquire_fetch(quota_units)
            except TinyFishQuotaExceeded:
                self._emit_telemetry(
                    operation=operation,
                    request_fingerprint=fingerprint,
                    started_at=started_at,
                    quota_units=quota_units,
                    attempts=attempt,
                    retry_count=max(0, attempt - 1),
                    cache_hit=cache_hit,
                    status="FAILED",
                    failure_code="QUOTA_EXHAUSTED",
                )
                raise

            request = Request(url, data=data, headers=headers, method=method)
            try:
                with urlopen(request, timeout=self._timeout_seconds) as response:
                    raw = response.read().decode("utf-8")
                    http_status = getattr(response, "status", None)
                payload = json.loads(raw)
                if not isinstance(payload, dict):
                    raise TinyFishMalformedResultError(
                        "TinyFish API returned a non-object JSON payload",
                        http_status=http_status,
                    )
                if cache is not None and ttl > 0:
                    cache.set(fingerprint, payload, ttl_seconds=ttl)
                self._emit_telemetry(
                    operation=operation,
                    request_fingerprint=fingerprint,
                    started_at=started_at,
                    quota_units=quota_units,
                    attempts=attempt + 1,
                    retry_count=attempt,
                    cache_hit=False,
                    status="SUCCEEDED",
                    http_status=http_status,
                )
                return payload
            except json.JSONDecodeError as exc:
                error = TinyFishMalformedResultError("TinyFish API returned invalid JSON")
                self._emit_failure(
                    operation, fingerprint, started_at, quota_units, attempt, error
                )
                raise error from exc
            except HTTPError as exc:
                error = self._classify_http_error(exc)
                if not error.retryable or attempt + 1 >= self._max_retry_attempts:
                    self._emit_failure(
                        operation, fingerprint, started_at, quota_units, attempt, error
                    )
                    raise error from exc
                self._emit_failure(
                    operation, fingerprint, started_at, quota_units, attempt, error
                )
                delay = self._retry_delay(exc, attempt)
                time.sleep(delay)
                last_error = error
            except URLError as exc:
                error = TinyFishNetworkError("TinyFish API request failed")
                if attempt + 1 >= self._max_retry_attempts:
                    self._emit_failure(
                        operation, fingerprint, started_at, quota_units, attempt, error
                    )
                    raise error from exc
                time.sleep(float(2**attempt) + 0.25 * (attempt + 1))
                last_error = error
            except TimeoutError as exc:
                error = TinyFishTimeoutError("TinyFish API request timed out")
                if attempt + 1 >= self._max_retry_attempts:
                    self._emit_failure(
                        operation, fingerprint, started_at, quota_units, attempt, error
                    )
                    raise error from exc
                time.sleep(float(2**attempt) + 0.25 * (attempt + 1))
                last_error = error

        if last_error is not None:
            self._emit_failure(
                operation,
                fingerprint,
                started_at,
                quota_units,
                self._max_retry_attempts - 1,
                last_error,
            )
            raise last_error
        error = TinyFishError("TinyFish API request failed")
        self._emit_failure(
            operation,
            fingerprint,
            started_at,
            quota_units,
            self._max_retry_attempts - 1,
            error,
        )
        raise error

    @staticmethod
    def _classify_http_error(exc: HTTPError) -> TinyFishError:
        if exc.code == 401:
            return TinyFishAuthError("TinyFish authentication failed", http_status=exc.code)
        if exc.code == 403:
            return TinyFishPolicyBlockError(
                "TinyFish request was blocked by provider policy",
                http_status=exc.code,
            )
        if exc.code in {400, 422}:
            return TinyFishInvalidRequestError(
                "TinyFish rejected the request",
                http_status=exc.code,
            )
        if exc.code == 429:
            return TinyFishRateLimitError(
                "TinyFish rate limit reached",
                http_status=exc.code,
            )
        if exc.code in {500, 502, 503, 504}:
            return TinyFishProviderError(
                "TinyFish provider returned a server error",
                http_status=exc.code,
            )
        return TinyFishError(
            f"TinyFish API returned HTTP {exc.code}",
            http_status=exc.code,
        )

    @staticmethod
    def _retry_delay(exc: HTTPError, attempt: int) -> float:
        retry_after = exc.headers.get("Retry-After")
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                pass
        return float(2**attempt) + 0.25 * (attempt + 1)

    def _emit_failure(
        self,
        operation: str,
        fingerprint: str,
        started_at: datetime,
        quota_units: int,
        attempt: int,
        error: TinyFishError,
    ) -> None:
        self._emit_telemetry(
            operation=operation,
            request_fingerprint=fingerprint,
            started_at=started_at,
            quota_units=quota_units,
            attempts=attempt + 1,
            retry_count=attempt,
            cache_hit=False,
            status="FAILED",
            http_status=error.http_status,
            failure_code=error.failure_code,
        )

    def _emit_telemetry(
        self,
        *,
        operation: str,
        request_fingerprint: str,
        started_at: datetime,
        quota_units: int,
        attempts: int,
        retry_count: int,
        cache_hit: bool,
        status: str,
        http_status: int | None = None,
        failure_code: str | None = None,
    ) -> None:
        if self._telemetry_sink is None:
            return
        finished_at = utc_now()
        latency_ms = max(
            0,
            int((finished_at - started_at).total_seconds() * 1000),
        )
        self._telemetry_sink(
            TinyFishRequestTelemetry(
                operation=operation,
                request_fingerprint=request_fingerprint,
                started_at=started_at,
                finished_at=finished_at,
                latency_ms=latency_ms,
                quota_units=quota_units,
                attempts=attempts,
                retry_count=retry_count,
                cache_hit=cache_hit,
                status=status,
                http_status=http_status,
                failure_code=failure_code,
            )
        )
