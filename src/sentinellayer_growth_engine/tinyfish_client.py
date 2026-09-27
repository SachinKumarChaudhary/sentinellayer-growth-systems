from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .tinyfish_rate_limit import TinyFishRateLimiter


class TinyFishError(RuntimeError):
    """Raised when a TinyFish Search or Fetch request cannot be completed."""


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
    """Small read-only adapter for TinyFish Search and Fetch APIs.

    Browser/Agent APIs are intentionally not exposed here. The growth
    enrichment workflow uses Search to discover public evidence and Fetch to
    read only URLs selected from that evidence.
    """

    def __init__(
        self,
        api_key: str,
        *,
        search_url: str = "https://api.search.tinyfish.ai",
        fetch_url: str = "https://api.fetch.tinyfish.ai",
        timeout_seconds: float = 30.0,
        rate_limiter: TinyFishRateLimiter | None = None,
        max_retry_attempts: int = 4,
    ) -> None:
        if not api_key.strip():
            raise ValueError("TinyFish API key is required")
        if timeout_seconds <= 0:
            raise ValueError("TinyFish timeout must be positive")
        self._api_key = api_key
        self._search_url = search_url
        self._fetch_url = fetch_url
        if max_retry_attempts <= 0:
            raise ValueError("TinyFish max_retry_attempts must be positive")
        self._timeout_seconds = timeout_seconds
        self._rate_limiter = rate_limiter or TinyFishRateLimiter()
        self._max_retry_attempts = max_retry_attempts

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

        params: dict[str, str] = {"query": query, "page": str(page)}
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
            "GET", f"{self._search_url}?{urlencode(params)}", quota_units=1
        )
        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            raise TinyFishError(
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
    ) -> list[TinyFishFetchResult]:
        """Fetch up to ten known public URLs using TinyFish's read-only API."""
        if not 1 <= len(urls) <= 10:
            raise ValueError("TinyFish Fetch accepts between 1 and 10 URLs")
        if any(
            not url.startswith(("http://", "https://")) for url in urls
        ):
            raise ValueError("TinyFish Fetch URLs must use http or https")
        if format not in {"markdown", "html", "json"}:
            raise ValueError(
                "TinyFish Fetch format must be markdown, html, or json"
            )

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
            "POST", self._fetch_url, body, quota_units=len(urls)
        )
        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            raise TinyFishError(
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
                    title=(
                        item.get("title")
                        if isinstance(item.get("title"), str)
                        else None
                    ),
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

    def _request_json(
        self,
        method: str,
        url: str,
        body: dict[str, Any] | None = None,
        *,
        quota_units: int = 1,
    ) -> dict[str, Any]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"X-API-Key": self._api_key, "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"

        last_error: TinyFishError | None = None
        for attempt in range(self._max_retry_attempts):
            if url.startswith(self._search_url):
                self._rate_limiter.acquire_search()
            else:
                self._rate_limiter.acquire_fetch(quota_units)
            request = Request(url, data=data, headers=headers, method=method)
            try:
                with urlopen(request, timeout=self._timeout_seconds) as response:
                    raw = response.read().decode("utf-8")
                payload = json.loads(raw)
                if not isinstance(payload, dict):
                    raise TinyFishError("TinyFish API returned a non-object JSON payload")
                return payload
            except json.JSONDecodeError as exc:
                raise TinyFishError("TinyFish API returned invalid JSON") from exc
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:500]
                last_error = TinyFishError(f"TinyFish API HTTP {exc.code}: {detail}")
                if exc.code not in {429, 500, 502, 503, 504}:
                    raise last_error from exc
                retry_after = exc.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = max(0.0, float(retry_after))
                    except ValueError:
                        delay = float(2**attempt)
                else:
                    delay = float(2**attempt)
                time.sleep(delay + 0.25 * (attempt + 1))
            except URLError as exc:
                last_error = TinyFishError(f"TinyFish API request failed: {exc.reason}")
                time.sleep(float(2**attempt) + 0.25 * (attempt + 1))
            except TimeoutError:
                last_error = TinyFishError("TinyFish API request timed out")
                time.sleep(float(2**attempt) + 0.25 * (attempt + 1))

        if last_error is not None:
            raise last_error
        raise TinyFishError("TinyFish API request failed")
