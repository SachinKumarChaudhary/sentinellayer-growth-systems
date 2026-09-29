from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

from .service import CRMActor, CRMService, CRMServiceError


ActorResolver = Callable[[dict[str, str]], CRMActor | None]


class CRMHTTPApplication:
    """Transport adapter implementing the frozen CRM HTTP contract."""

    def __init__(self, service: CRMService, actor_resolver: ActorResolver) -> None:
        self.service = service
        self.actor_resolver = actor_resolver
    @staticmethod
    def _request_id(headers: dict[str, str]) -> str:
        value = headers.get("x-request-id", "").strip()
        return value[:128] if value else f"crm-{uuid4()}"

    @staticmethod
    def _body_value(body: dict[str, Any], name: str) -> Any:
        if name not in body:
            raise CRMServiceError("INVALID_INPUT", f"missing field: {name}")
        return body[name]

    @staticmethod
    def _json_error(exc: CRMServiceError) -> tuple[int, dict[str, Any]]:
        status = {
            "INVALID_INPUT": 400,
            "NOT_FOUND": 404,
            "FORBIDDEN": 403,
            "SUPPRESSED": 409,
            "STATE_TRANSITION_INVALID": 422,
            "CONFLICT": 409,
            "RELATIONSHIP_INVALID": 422,
        }.get(exc.code, 500)
        return status, {"error": {"code": exc.code, "message": exc.message, "field_errors": []}}
    def handle(
        self, *, method: str, target: str, headers: dict[str, str],
        body: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        body = dict(body or {})
        body.setdefault("idempotency_key", headers.get("idempotency-key"))
        request_id = self._request_id(headers)
        parsed = urlsplit(target)
        path = parsed.path.rstrip("/") or "/"
        query = parse_qs(parsed.query)
        try:
            actor = self.actor_resolver(headers)
            if path == "/healthz" and method == "GET":
                return 200, {"data": {"status": "ok"}, "meta": {"request_id": request_id}}
            if path == "/v1/crm/search" and method == "GET":
                term = query.get("q", [""])[0]
                return 200, self.service.search_accounts(query=term)
            if path == "/v1/crm/accounts" and method == "GET":
                return self._accounts(query)
            if path == "/v1/crm/contacts" and method == "GET":
                return self._contacts(query)
            if path == "/v1/crm/pipeline" and method == "GET":
                return 200, self.service.pipeline()
            if path == "/v1/crm/tasks" and method == "GET":
                limit = int(query.get("limit", ["100"])[0])
                return 200, self.service.task_queue(limit=limit)
            if path.startswith("/v1/crm/accounts/"):
                return self._account_route(method, path, headers, body, actor, request_id)
            if path.startswith("/v1/crm/contacts/"):
                return self._contact_route(method, path, headers, body, actor, request_id)
            if path == "/v1/crm/activities" and method == "POST":
                return self._create_activity(body, actor, request_id)
            if path == "/v1/crm/tasks" and method == "POST":
                return self._create_task(body, actor, request_id)
            if path == "/v1/crm/notes" and method == "POST":
                return self._create_note(body, actor, request_id)
            return 404, {"error": {"code": "NOT_FOUND", "message": "route not found", "field_errors": []}}
        except CRMServiceError as exc:
            status, payload = self._json_error(exc)
            payload["meta"] = {"request_id": request_id}
            return status, payload
        except (ValueError, TypeError) as exc:
            return 400, {"error": {"code": "INVALID_INPUT", "message": str(exc), "field_errors": []}, "meta": {"request_id": request_id}}
    def _accounts(self, query: dict[str, list[str]]) -> tuple[int, dict[str, Any]]:
        limit = int(query.get("limit", ["50"])[0])
        after_raw = query.get("after_cursor", [None])[0]
        after_id = int(after_raw) if after_raw else None
        state = query.get("state", [None])[0]
        owner_raw = query.get("owner", [None])[0]
        owner = UUID(owner_raw) if owner_raw else None
        return 200, self.service.accounts(
            query=query.get("q", [None])[0], state=state,
            owner_user_id=owner, after_id=after_id, limit=limit,
        )

    def _contacts(self, query: dict[str, list[str]]) -> tuple[int, dict[str, Any]]:
        limit = int(query.get("limit", ["50"])[0])
        after_raw = query.get("after_cursor", [None])[0]
        after_id = UUID(after_raw) if after_raw else None
        account_raw = query.get("account_id", [None])[0]
        account_id = int(account_raw) if account_raw else None
        return 200, self.service.contacts(
            query=query.get("q", [None])[0], account_id=account_id,
            state=query.get("state", [None])[0], channel=query.get("channel", [None])[0],
            after_id=after_id, limit=limit,
        )

    def _account_route(
        self, method: str, path: str, headers: dict[str, str],
        body: dict[str, Any], actor: CRMActor | None, request_id: str,
    ) -> tuple[int, dict[str, Any]]:
        parts = path.split("/")
        account_id = int(parts[4])
        if len(parts) == 5 and method == "GET":
            return 200, self.service.account_360(account_id=account_id)
        if len(parts) == 6 and parts[5] == "state-transitions" and method == "POST":
            return 200, self.service.transition_account(
                account_id=account_id,
                to_state=str(self._body_value(body, "to_state")),
                expected_version=int(self._body_value(body, "expected_version")),
                reason=body.get("reason"),
                actor=actor,
                request_id=request_id,
                idempotency_key=headers.get("idempotency-key"),
                explicit_unsuppress=bool(body.get("explicit_unsuppress", False)),
            )
        return 404, {"error": {"code": "NOT_FOUND", "message": "account route not found", "field_errors": []}}
    def _contact_route(
        self, method: str, path: str, headers: dict[str, str],
        body: dict[str, Any], actor: CRMActor | None, request_id: str,
    ) -> tuple[int, dict[str, Any]]:
        parts = path.split("/")
        person_id = UUID(parts[4])
        if len(parts) == 6 and parts[5] == "state-transitions" and method == "POST":
            return 200, self.service.transition_contact(
                decision_maker_id=person_id,
                to_state=str(self._body_value(body, "to_state")),
                expected_version=int(self._body_value(body, "expected_version")),
                reason=body.get("reason"),
                actor=actor,
                request_id=request_id,
                idempotency_key=headers.get("idempotency-key"),
                explicit_unsuppress=bool(body.get("explicit_unsuppress", False)),
            )
        return 404, {"error": {"code": "NOT_FOUND", "message": "contact route not found", "field_errors": []}}
    def _create_activity(
        self, body: dict[str, Any], actor: CRMActor | None, request_id: str
    ) -> tuple[int, dict[str, Any]]:
        occurred_at = datetime.fromisoformat(str(self._body_value(body, "occurred_at")).replace("Z", "+00:00"))
        person = body.get("decision_maker_id")
        return 201, self.service.create_activity(
            account_id=int(self._body_value(body, "account_id")),
            channel=str(self._body_value(body, "channel")),
            activity_type=str(self._body_value(body, "activity_type")),
            occurred_at=occurred_at,
            summary=str(self._body_value(body, "summary")),
            actor=actor,
            decision_maker_id=UUID(person) if person else None,
            direction=str(body.get("direction", "outbound")),
            reference=body.get("reference"),
            request_id=request_id,
            idempotency_key=body.get("idempotency_key"),
        )
    def _create_task(
        self, body: dict[str, Any], actor: CRMActor | None, request_id: str
    ) -> tuple[int, dict[str, Any]]:
        person = body.get("decision_maker_id")
        assigned = body.get("assigned_to")
        due_raw = body.get("due_at")
        due_at = datetime.fromisoformat(str(due_raw).replace("Z", "+00:00")) if due_raw else None
        return 201, self.service.create_task(
            account_id=int(self._body_value(body, "account_id")),
            recommended_action=str(self._body_value(body, "recommended_action")),
            trigger_type=str(self._body_value(body, "trigger_type")),
            priority=str(self._body_value(body, "priority")),
            actor=actor,
            due_at=due_at,
            decision_maker_id=UUID(person) if person else None,
            assigned_to=UUID(assigned) if assigned else None,
            why_now=body.get("why_now"),
            source_event_type=body.get("source_event_type"),
            source_event_id=body.get("source_event_id"),
            request_id=request_id,
            idempotency_key=body.get("idempotency_key"),
        )
    def _create_note(
        self, body: dict[str, Any], actor: CRMActor | None, request_id: str
    ) -> tuple[int, dict[str, Any]]:
        person = body.get("decision_maker_id")
        return 201, self.service.create_note(
            body=str(self._body_value(body, "body")),
            actor=actor,
            account_id=int(body["account_id"]) if body.get("account_id") is not None else None,
            decision_maker_id=UUID(person) if person else None,
            request_id=request_id,
            idempotency_key=body.get("idempotency_key"),
        )
def build_crm_application(
    service: CRMService, actor_resolver: ActorResolver
) -> CRMHTTPApplication:
    return CRMHTTPApplication(service, actor_resolver)
