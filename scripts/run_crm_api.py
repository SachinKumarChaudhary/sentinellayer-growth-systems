from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from uuid import UUID

import psycopg

from sentinellayer_growth_engine.config import Settings
from sentinellayer_growth_engine.crm import CRMActor, CRMHTTPApplication, CRMReadModelRepository, CRMRepository, CRMService


def build_service(settings: Settings) -> CRMService:
    def connection_factory() -> psycopg.Connection[Any]:
        return psycopg.connect(
            settings.database_url,
            connect_timeout=settings.database_connect_timeout_seconds,
            options=f"-c statement_timeout={settings.database_statement_timeout_seconds}",
        )
    return CRMService(
        write_repo=CRMRepository(connection_factory),
        read_repo=CRMReadModelRepository(connection_factory),
    )
def build_handler(application: CRMHTTPApplication) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "SentinelLayerCRM/1"

        def _send(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, default=str, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _headers(self) -> dict[str, str]:
            return {key.lower(): value for key, value in self.headers.items()}
        def _body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 1024 * 1024:
                raise ValueError("request body exceeds 1 MiB")
            if length == 0:
                return {}
            raw = self.rfile.read(length)
            parsed = json.loads(raw.decode("utf-8"))
            if not isinstance(parsed, dict):
                raise ValueError("JSON body must be an object")
            return parsed

        def do_GET(self) -> None:
            self._dispatch("GET")

        def do_POST(self) -> None:
            self._dispatch("POST")

        def _dispatch(self, method: str) -> None:
            try:
                body = self._body() if method == "POST" else {}
                status, payload = application.handle(
                    method=method,
                    target=self.path,
                    headers=self._headers(),
                    body=body,
                )
            except (ValueError, json.JSONDecodeError) as exc:
                status = 400
                payload = {"error": {"code": "INVALID_INPUT", "message": str(exc), "field_errors": []}}
            except Exception:
                status = 500
                payload = {"error": {"code": "INTERNAL", "message": "CRM request failed", "field_errors": []}}
            self._send(status, payload)

        def log_message(self, fmt: str, *args: object) -> None:
            return

    return Handler
def main() -> int:
    settings = Settings(database_url=os.environ.get("SL_DATABASE_URL", ""))
    if settings.environment != "development":
        raise RuntimeError("run_crm_api.py is development-only; production auth must be injected by deployment")
    if not settings.database_url:
        raise RuntimeError("SL_DATABASE_URL is required")
    actor_raw = os.environ.get("SL_CRM_DEV_ACTOR_USER_ID", "")
    if not actor_raw:
        raise RuntimeError("SL_CRM_DEV_ACTOR_USER_ID is required for local mutation testing")
    actor = CRMActor(user_id=UUID(actor_raw))
    service = build_service(settings)
    application = CRMHTTPApplication(service, lambda _headers: actor)
    host = "127.0.0.1"
    port = int(os.environ.get("SL_CRM_PORT", "8090"))
    server = ThreadingHTTPServer((host, port), build_handler(application))
    print(f"CRM development API listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
