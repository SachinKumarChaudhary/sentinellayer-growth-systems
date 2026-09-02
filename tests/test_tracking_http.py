from __future__ import annotations

import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

from sentinellayer_growth_engine.tracking_http import make_handler
from sentinellayer_growth_engine.tracking_service import IngestionResult


class FakeTrackingService:
    def __init__(self, result: IngestionResult) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def ingest_link_request(self, **kwargs: object) -> IngestionResult:
        self.calls.append(kwargs)
        return self.result


def _serve(service: FakeTrackingService):
    handler = make_handler(
        database_url="postgresql://unused",
        environment="development",
        tracking_hash_secret="test-secret",
        service=service,
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _request(server: ThreadingHTTPServer, method: str, path: str):
    conn = HTTPConnection("127.0.0.1", server.server_address[1], timeout=3)
    conn.request(
        method,
        path,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html",
            "Sec-Fetch-Mode": "navigate",
        },
    )
    response = conn.getresponse()
    headers = dict(response.getheaders())
    body = response.read()
    conn.close()
    return response.status, headers, body


def test_get_valid_tracking_token_redirects_and_records_request() -> None:
    service = FakeTrackingService(
        IngestionResult(True, None, "human_candidate", "https://example.com/landing")
    )
    server, thread = _serve(service)
    try:
        status, headers, body = _request(
            server, "GET", "/t/AbCdEfGhIjKlMnOpQrStUvWxYz123456"
        )
        assert status == 302
        assert headers["Location"] == "https://example.com/landing"
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert body == b""
        assert len(service.calls) == 1
        assert service.calls[0]["public_token"] == "AbCdEfGhIjKlMnOpQrStUvWxYz123456"
    finally:
        server.shutdown()
        thread.join(timeout=3)
        server.server_close()


def test_invalid_token_returns_404_without_ingestion() -> None:
    service = FakeTrackingService(IngestionResult(False, None, "unknown", None))
    server, thread = _serve(service)
    try:
        status, _, body = _request(server, "GET", "/t/not-valid")
        assert status == 404
        assert body == b'{"error":"not_found"}'
        assert service.calls == []
    finally:
        server.shutdown()
        thread.join(timeout=3)
        server.server_close()


def test_asset_route_is_not_exposed_until_contract_is_defined() -> None:
    service = FakeTrackingService(
        IngestionResult(True, None, "human_candidate", "https://example.com")
    )
    server, thread = _serve(service)
    try:
        status, _, _ = _request(
            server, "GET", "/a/AbCdEfGhIjKlMnOpQrStUvWxYz123456"
        )
        assert status == 404
        assert service.calls == []
    finally:
        server.shutdown()
        thread.join(timeout=3)
        server.server_close()


def test_post_is_rejected() -> None:
    service = FakeTrackingService(IngestionResult(False, None, "unknown", None))
    server, thread = _serve(service)
    try:
        status, _, body = _request(
            server, "POST", "/t/AbCdEfGhIjKlMnOpQrStUvWxYz123456"
        )
        assert status == 405
        assert body == b'{"error":"method_not_allowed"}'
    finally:
        server.shutdown()
        thread.join(timeout=3)
        server.server_close()
