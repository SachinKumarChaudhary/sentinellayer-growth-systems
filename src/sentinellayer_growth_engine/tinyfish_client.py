from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


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
    ) -> None:
        if not api_key.strip():
            raise ValueError("TinyFish API key is required")
        if timeout_seconds <= 0:
            raise ValueError("TinyFish timeout must be positive")
        self._api_key = api_key
        self._search_url = search_url
        self._fetch_url = fetch_url
        self._timeout_seconds = timeout_seconds

    def search(self, query: str, *, purpose: str | None = None) -> list[TinyFishSearchResult]:
        """Run one public-web search and return structured results."""
        if not query.strip():
            raise ValueError("TinyFish search query must not be empty")
        params: dict[str, str] = {"query": query}
        if purpose:
            params["purpose"] = purpose
        payload = self._request_json("GET", f"{self._search_url}?{urlencode(params)}")
        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            raise TinyFishError("TinyFish Search returned an invalid results payload")
        results: list[TinyFishSearchResult] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            title = item.get("title")
            url = item.get("url")
            snippet = item.get("snippet", "")
            if isinstance(title, str) and isinstance(url, str) and isinstance(snippet, str):
                results.append(TinyFishSearchResult(title=title, url=url, snippet=snippet))
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
        if any(not url.startswith(("http://", "https://")) for url in urls):
            raise ValueError("TinyFish Fetch URLs must use http or https")
        if format not in {"markdown", "html", "json"}:
            raise ValueError("TinyFish Fetch format must be markdown, html, or json")

        body: dict[str, Any] = {
            "urls": urls,
            "format": format,
            "links": include_links,
            "image_links": include_image_links,
            "page_metadata": include_page_metadata,
        }
        if purpose:
            body["purpose"] = purpose
        payload = self._request_json("POST", self._fetch_url, body)
        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            raise TinyFishError("TinyFish Fetch returned an invalid results payload")
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
                    final_url=item.get("final_url")
                    if isinstance(item.get("final_url"), str)
                    else None,
                    published_date=item.get("published_date")
                    if isinstance(item.get("published_date"), str)
                    else None,
                )
            )
        return results

    def _request_json(
        self, method: str, url: str, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"X-API-Key": self._api_key, "Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise TinyFishError(f"TinyFish API HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise TinyFishError(f"TinyFish API request failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise TinyFishError("TinyFish API request timed out") from exc

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TinyFishError("TinyFish API returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise TinyFishError("TinyFish API returned a non-object JSON payload")
        return payload
