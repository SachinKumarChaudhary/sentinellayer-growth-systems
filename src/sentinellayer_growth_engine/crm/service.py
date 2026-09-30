from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from .read_models import CRMReadModelRepository
from .repository import CRMConflictError, CRMNotFoundError, CRMRepository
from .state import StateTransitionError


@dataclass(frozen=True)
class CRMActor:
    user_id: UUID
    role: str | None = None


class CRMServiceError(RuntimeError):
    """Base service-boundary error with a stable API error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
class CRMService:
    def __init__(
        self,
        *,
        write_repo: CRMRepository,
        read_repo: CRMReadModelRepository,
    ) -> None:
        self._write = write_repo
        self._read = read_repo

    @staticmethod
    def _require_actor(actor: CRMActor | None) -> CRMActor:
        if actor is None:
            raise CRMServiceError("FORBIDDEN", "authenticated actor is required")
        return actor

    def authorize(self, actor: CRMActor | None, *, mutation: bool = False) -> CRMActor:
        actor = self._require_actor(actor)
        try:
            access = self._write.get_user_access(user_id=actor.user_id)
        except Exception as exc:
            raise self._map_error(exc) from exc
        if not access or not access.get("active"):
            raise CRMServiceError("FORBIDDEN", "CRM membership is inactive or missing")
        role = str(access.get("role"))
        if mutation and role not in {"OPERATOR", "ADMIN"}:
            raise CRMServiceError("FORBIDDEN", "CRM role is read-only")
        return CRMActor(user_id=actor.user_id, role=role)

    @staticmethod
    def _map_error(exc: Exception) -> CRMServiceError:
        if isinstance(exc, CRMNotFoundError):
            return CRMServiceError("NOT_FOUND", str(exc))
        if isinstance(exc, CRMConflictError):
            return CRMServiceError("CONFLICT", str(exc))
        if isinstance(exc, StateTransitionError):
            message = str(exc)
            code = "SUPPRESSED" if "SUPPRESSED" in message else "STATE_TRANSITION_INVALID"
            return CRMServiceError(code, message)
        if isinstance(exc, ValueError):
            return CRMServiceError("INVALID_INPUT", str(exc))
        return CRMServiceError("INTERNAL", "CRM operation failed")
    def accounts(
        self, *, query: str | None = None, state: str | None = None,
        owner_user_id: UUID | None = None, after_id: int | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        try:
            return self._read.list_accounts(
                query=query, state=state, owner_user_id=owner_user_id,
                after_id=after_id, limit=limit,
            )
        except Exception as exc:
            raise self._map_error(exc) from exc

    def search_accounts(self, *, query: str, limit: int = 25) -> dict[str, Any]:
        try:
            data = self._read.search_accounts(query=query, limit=limit)
            return {"data": data, "meta": {"has_more": len(data) == limit}}
        except Exception as exc:
            raise self._map_error(exc) from exc

    def contacts(
        self, *, query: str | None = None, account_id: int | None = None,
        state: str | None = None, channel: str | None = None,
        after_id: UUID | None = None, limit: int = 50,
    ) -> dict[str, Any]:
        try:
            return self._read.list_contacts(
                query=query, account_id=account_id, state=state,
                channel=channel, after_id=after_id, limit=limit,
            )
        except Exception as exc:
            raise self._map_error(exc) from exc

    def contact_360(self, *, decision_maker_id: UUID) -> dict[str, Any]:
        try:
            return {"data": self._read.get_contact_360(decision_maker_id=decision_maker_id), "meta": {}}
        except Exception as exc:
            raise self._map_error(exc) from exc

    def pipeline(self) -> dict[str, Any]:
        try:
            return self._read.pipeline_summary()
        except Exception as exc:
            raise self._map_error(exc) from exc

    def account_360(self, *, account_id: int) -> dict[str, Any]:
        try:
            return {"data": self._read.get_account_360(account_id=account_id), "meta": {}}
        except Exception as exc:
            raise self._map_error(exc) from exc

    def update_account_fields(
        self, *, account_id: int, fields: dict[str, Any], actor: CRMActor,
        request_id: str | None = None, idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        actor = self._require_actor(actor)
        try:
            data = self._write.update_account_fields(
                account_id=account_id, fields=fields, actor_user_id=actor.user_id,
                request_id=request_id, idempotency_key=idempotency_key,
            )
            return {"data": data, "meta": {"request_id": request_id}}
        except Exception as exc:
            raise self._map_error(exc) from exc

    def update_contact_fields(
        self, *, decision_maker_id: UUID, fields: dict[str, Any], actor: CRMActor,
        request_id: str | None = None, idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        actor = self._require_actor(actor)
        try:
            data = self._write.update_contact_fields(
                decision_maker_id=decision_maker_id, fields=fields, actor_user_id=actor.user_id,
                request_id=request_id, idempotency_key=idempotency_key,
            )
            return {"data": data, "meta": {"request_id": request_id}}
        except Exception as exc:
            raise self._map_error(exc) from exc

    def export(self, *, entity: str, actor: CRMActor, limit: int = 5000) -> dict[str, Any]:
        self._require_actor(actor)
        try:
            data=self._write.export_records(entity=entity,limit=limit)
            return {"data":data,"meta":{"entity":entity,"count":len(data)}}
        except Exception as exc:
            raise self._map_error(exc) from exc

    def opportunities(self, *, account_id: int | None = None, owner_user_id: UUID | None = None, stage: str | None = None, limit: int = 100) -> dict[str, Any]:
        try:
            data=self._write.list_opportunities(account_id=account_id,owner_user_id=owner_user_id,stage=stage,limit=limit)
            return {"data":data,"meta":{"has_more":len(data)==limit}}
        except Exception as exc:
            raise self._map_error(exc) from exc

    def opportunity(self, *, opportunity_id: UUID) -> dict[str, Any]:
        try:
            return {"data":self._write.get_opportunity(opportunity_id=opportunity_id),"meta":{}}
        except Exception as exc:
            raise self._map_error(exc) from exc

    def create_opportunity(self, *, account_id: int, name: str, owner_user_id: UUID, actor: CRMActor,
                           primary_contact_id: UUID | None = None, stage: str = 'QUALIFIED', value: Any = None,
                           currency: str | None = None, expected_close_date: Any = None, next_task_id: UUID | None = None,
                           notes: str | None = None, closed_reason: str | None = None, request_id: str | None = None,
                           idempotency_key: str | None = None) -> dict[str, Any]:
        actor=self._require_actor(actor)
        try:
            data=self._write.create_opportunity(account_id=account_id,name=name,owner_user_id=owner_user_id,actor_user_id=actor.user_id,
                primary_contact_id=primary_contact_id,stage=stage,value=value,currency=currency,expected_close_date=expected_close_date,
                next_task_id=next_task_id,notes=notes,closed_reason=closed_reason,request_id=request_id,idempotency_key=idempotency_key)
            return {"data":data,"meta":{"request_id":request_id}}
        except Exception as exc:
            raise self._map_error(exc) from exc

    def update_opportunity(self, *, opportunity_id: UUID, fields: dict[str, Any], expected_version: int, actor: CRMActor,
                           request_id: str | None = None, idempotency_key: str | None = None) -> dict[str, Any]:
        actor=self._require_actor(actor)
        try:
            data=self._write.update_opportunity(opportunity_id=opportunity_id,fields=fields,expected_version=expected_version,actor_user_id=actor.user_id,request_id=request_id,idempotency_key=idempotency_key)
            return {"data":data,"meta":{"request_id":request_id}}
        except Exception as exc:
            raise self._map_error(exc) from exc

    def transition_opportunity(self, *, opportunity_id: UUID, to_stage: str, expected_version: int, actor: CRMActor,
                               closed_reason: str | None = None, request_id: str | None = None, idempotency_key: str | None = None) -> dict[str, Any]:
        actor=self._require_actor(actor)
        try:
            data=self._write.transition_opportunity(opportunity_id=opportunity_id,to_stage=to_stage,expected_version=expected_version,actor_user_id=actor.user_id,closed_reason=closed_reason,request_id=request_id,idempotency_key=idempotency_key)
            return {"data":data,"meta":{"request_id":request_id}}
        except Exception as exc:
            raise self._map_error(exc) from exc

    def crm_members(self) -> dict[str, Any]:
        try:
            return {"data": self._write.list_crm_members(), "meta": {}}
        except Exception as exc:
            raise self._map_error(exc) from exc

    def initialize_account(
        self, *, account_id: int, actor: CRMActor,
        request_id: str | None = None, idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        actor = self._require_actor(actor)
        try:
            data = self._write.initialize_account_state(
                account_id=account_id,
                actor_user_id=actor.user_id,
                request_id=request_id,
                idempotency_key=idempotency_key,
            )
            return {"data": data, "meta": {"request_id": request_id}}
        except Exception as exc:
            raise self._map_error(exc) from exc

    def transition_account(
        self, *, account_id: int, to_state: str, expected_version: int,
        actor: CRMActor, reason: str | None = None,
        request_id: str | None = None, idempotency_key: str | None = None,
        explicit_unsuppress: bool = False,
    ) -> dict[str, Any]:
        actor = self._require_actor(actor)
        try:
            data = self._write.transition_account_state(
                account_id=account_id, to_state=to_state,
                expected_version=expected_version, actor_user_id=actor.user_id,
                reason=reason, request_id=request_id,
                idempotency_key=idempotency_key,
                explicit_unsuppress=explicit_unsuppress,
            )
            return {"data": data, "meta": {"request_id": request_id}}
        except Exception as exc:
            raise self._map_error(exc) from exc
    def transition_contact(
        self, *, decision_maker_id: UUID, to_state: str, expected_version: int,
        actor: CRMActor, reason: str | None = None,
        request_id: str | None = None, idempotency_key: str | None = None,
        explicit_unsuppress: bool = False,
    ) -> dict[str, Any]:
        actor = self._require_actor(actor)
        try:
            data = self._write.transition_contact_state(
                decision_maker_id=decision_maker_id, to_state=to_state,
                expected_version=expected_version, actor_user_id=actor.user_id,
                reason=reason, request_id=request_id,
                idempotency_key=idempotency_key,
                explicit_unsuppress=explicit_unsuppress,
            )
            return {"data": data, "meta": {"request_id": request_id}}
        except Exception as exc:
            raise self._map_error(exc) from exc

    def create_note(
        self, *, body: str, actor: CRMActor, account_id: int | None = None,
        decision_maker_id: UUID | None = None, request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        actor = self._require_actor(actor)
        try:
            data = self._write.create_note(
                body=body, author_user_id=actor.user_id, account_id=account_id,
                decision_maker_id=decision_maker_id, request_id=request_id,
                idempotency_key=idempotency_key,
            )
            return {"data": data, "meta": {"request_id": request_id}}
        except Exception as exc:
            raise self._map_error(exc) from exc

    def create_activity(
        self, *, account_id: int, channel: str, activity_type: str,
        occurred_at: datetime, summary: str, actor: CRMActor,
        decision_maker_id: UUID | None = None, direction: str = "outbound",
        reference: str | None = None, request_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        actor = self._require_actor(actor)
        try:
            data = self._write.create_manual_activity(
                account_id=account_id, channel=channel,
                activity_type=activity_type, occurred_at=occurred_at,
                summary=summary, actor_user_id=actor.user_id,
                decision_maker_id=decision_maker_id, direction=direction,
                reference=reference, request_id=request_id, idempotency_key=idempotency_key,
            )
            return {"data": data, "meta": {"request_id": request_id}}
        except Exception as exc:
            raise self._map_error(exc) from exc
    def create_task(
        self, *, account_id: int, recommended_action: str,
        trigger_type: str, priority: str, actor: CRMActor,
        due_at: datetime | None = None, decision_maker_id: UUID | None = None,
        assigned_to: UUID | None = None, why_now: list[Any] | None = None,
        source_event_type: str | None = None, source_event_id: str | None = None,
        request_id: str | None = None, idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        actor = self._require_actor(actor)
        try:
            data = self._write.create_task(
                account_id=account_id, recommended_action=recommended_action,
                trigger_type=trigger_type, priority=priority, due_at=due_at,
                decision_maker_id=decision_maker_id, assigned_to=assigned_to,
                why_now=why_now, source_event_type=source_event_type,
                source_event_id=source_event_id, actor_user_id=actor.user_id,
                request_id=request_id, idempotency_key=idempotency_key,
            )
            return {"data": data, "meta": {"request_id": request_id}}
        except Exception as exc:
            raise self._map_error(exc) from exc

    def task_queue(self, *, limit: int = 100) -> dict[str, Any]:
        try:
            data = self._write.list_task_queue(limit=limit)
            return {"data": data, "meta": {"has_more": len(data) == limit}}
        except Exception as exc:
            raise self._map_error(exc) from exc

    def bulk_state(
        self, *, account_ids: list[int], to_state: str,
        expected_versions: dict[int, int], actor: CRMActor,
        request_id: str | None = None, idempotency_key: str | None = None,
        explicit_unsuppress: bool = False,
    ) -> dict[str, Any]:
        actor = self._require_actor(actor)
        if not account_ids:
            raise CRMServiceError("INVALID_INPUT", "account_ids must not be empty")
        try:
            results = self._write.bulk_transition_accounts(
                account_ids=account_ids, to_state=to_state,
                expected_versions=expected_versions, actor_user_id=actor.user_id,
                request_id=request_id, idempotency_key=idempotency_key,
                explicit_unsuppress=explicit_unsuppress,
            )
            return self._bulk_envelope(results, request_id)
        except Exception as exc:
            raise self._map_error(exc) from exc

    def bulk_assign(
        self, *, account_ids: list[int], owner_user_id: UUID | None,
        expected_versions: dict[int, int], actor: CRMActor,
        request_id: str | None = None, idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        actor = self._require_actor(actor)
        if not account_ids:
            raise CRMServiceError("INVALID_INPUT", "account_ids must not be empty")
        try:
            results = self._write.bulk_assign_accounts(
                account_ids=account_ids, owner_user_id=owner_user_id,
                expected_versions=expected_versions, actor_user_id=actor.user_id,
                request_id=request_id, idempotency_key=idempotency_key,
            )
            return self._bulk_envelope(results, request_id)
        except Exception as exc:
            raise self._map_error(exc) from exc

    @staticmethod
    def _bulk_envelope(results: list[dict[str, Any]], request_id: str | None) -> dict[str, Any]:
        success = sum(1 for item in results if item["status"] == "success")
        failed = len(results) - success
        return {
            "data": results,
            "meta": {
                "request_id": request_id,
                "total": len(results),
                "succeeded": success,
                "failed": failed,
                "partial_failure": success > 0 and failed > 0,
            },
        }
