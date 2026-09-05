from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

import psycopg

from .tracking import hash_ip
from .tracking_repository import TrackingRepository
from .tracking_service import TrackingService

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{20,128}$")
_MAX_USER_AGENT = 2048
_MAX_HEADER = 8192


def _bounded(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    return value[:limit]


def _client_ip(handler: BaseHTTPRequestHandler) -> str | None:
    # Do not trust X-Forwarded-For by default. A deployment-specific trusted
    # proxy may normalize the source address before this service is exposed.
    return handler.client_address[0] if handler.client_address else None


def make_handler(
    *,
    database_url: str,
    environment: str,
    tracking_hash_secret: str,
    service: TrackingService | None = None,
) -> type[BaseHTTPRequestHandler]:
    if not database_url:
        raise ValueError("database_url is required")
    if not tracking_hash_secret:
        raise ValueError("tracking_hash_secret is required")
    if environment not in {"development", "staging", "production"}:
        raise ValueError("invalid environment")

    if service is None:
        def connection_factory() -> psycopg.Connection:
            return psycopg.connect(database_url)
        service = TrackingService(TrackingRepository(connection_factory))

    class TrackingHandler(BaseHTTPRequestHandler):
        server_version = "SentinelLayerTracking/1"

        def _security_headers(self) -> None:
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
            self.send_header("X-Robots-Tag", "noindex, nofollow")

        def _json(self, status: int, payload: dict[str, object]) -> None:
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self._security_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _redirect(self, destination: str) -> None:
            self.send_response(302)
            self._security_headers()
            self.send_header("Location", destination)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _token_from_path(self) -> str | None:
            parsed = urlparse(self.path)
            parts = [unquote(part) for part in parsed.path.split("/") if part]
            if len(parts) != 2 or parts[0] not in {"t", "a"}:
                return None
            token = parts[1]
            return token if _TOKEN_RE.fullmatch(token) else None

        def _handle_tracking(self) -> None:
            token = self._token_from_path()
            if token is None:
                self._json(404, {"error": "not_found"})
                return

            parsed = urlparse(self.path)
            prefix = parsed.path.split("/")[1]
            # Asset-token ingestion stays behind its own contract until semantics are fixed.
            if prefix != "t":
                self._json(404, {"error": "not_found"})
                return
            user_agent = _bounded(self.headers.get("User-Agent"), _MAX_USER_AGENT)
            accept = _bounded(self.headers.get("Accept"), _MAX_HEADER)
            sec_ch_ua = _bounded(self.headers.get("Sec-CH-UA"), _MAX_HEADER)
            sec_fetch_mode = _bounded(self.headers.get("Sec-Fetch-Mode"), _MAX_HEADER)
            referrer = _bounded(self.headers.get("Referer"), _MAX_HEADER)
            ip = _client_ip(self)
            ip_digest = hash_ip(ip, secret=tracking_hash_secret) if ip else None

            # The token itself is the only client-controlled identity. All
            # account/person/campaign/send identifiers are resolved server-side.
            try:
                result = service.ingest_link_request(
                    public_token=token,
                    environment=environment,
                    source_system="tracking_http",
                    correlation_id=f"http:{token}:{self.command}:{self.headers.get('X-Request-ID', '')[:128]}",
                    user_agent=user_agent,
                    method=self.command,
                    accept=accept,
                    sec_ch_ua=sec_ch_ua,
                    sec_fetch_mode=sec_fetch_mode,
                    referrer=referrer,
                    ip_hash=ip_digest,
                )

                if result.destination_url is None:
                    self._json(404, {"error": "not_found"})
                    return
                self._redirect(result.destination_url)
            except (ValueError, psycopg.Error):
                logger.exception("tracking request failed")
                # Never leak database/runtime details to the client.
                self._json(503, {"error": "temporarily_unavailable"})

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/healthz":
                self._json(200, {"status": "ok"})
                return
            if parsed.path == "/readyz":
                try:
                    with psycopg.connect(database_url) as conn, conn.cursor() as cur:
                        cur.execute("select 1")
                        cur.fetchone()
                    self._json(200, {"status": "ready"})
                except psycopg.Error:
                    self._json(503, {"status": "not_ready"})
                return
            self._handle_tracking()

        def do_HEAD(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/healthz":
                self._json(200, {"status": "ok"})
                return
            if parsed.path == "/readyz":
                try:
                    with psycopg.connect(database_url) as conn, conn.cursor() as cur:
                        cur.execute("select 1")
                        cur.fetchone()
                    self._json(200, {"status": "ready"})
                except psycopg.Error:
                    self._json(503, {"status": "not_ready"})
                return
            self._handle_tracking()

        def do_POST(self) -> None:
            self._json(405, {"error": "method_not_allowed"})

        def log_message(self, fmt: str, *args: object) -> None:
            logger.info("%s - %s", self.address_string(), fmt % args)

    return TrackingHandler


def run_server(
    *,
    database_url: str,
    environment: str,
    tracking_hash_secret: str,
    host: str = "127.0.0.1",
    port: int = 8080,
    server_factory: Callable[..., ThreadingHTTPServer] = ThreadingHTTPServer,
) -> None:
    handler = make_handler(
        database_url=database_url,
        environment=environment,
        tracking_hash_secret=tracking_hash_secret,
    )
    server = server_factory((host, port), handler)
    logger.info("tracking HTTP service listening on %s:%s", host, port)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main() -> None:
    logging.basicConfig(level=os.getenv("SL_LOG_LEVEL", "INFO"))
    run_server(
        database_url=os.environ["SL_DATABASE_URL"],
        environment=os.getenv("SL_ENVIRONMENT", "development"),
        tracking_hash_secret=os.environ["SL_TRACKING_HASH_SECRET"],
        host=os.getenv("SL_TRACKING_HOST", "127.0.0.1"),
        port=int(os.getenv("SL_TRACKING_PORT", "8080")),
    )


if __name__ == "__main__":
    main()
