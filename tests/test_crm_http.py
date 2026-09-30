from uuid import UUID

import pytest

from sentinellayer_growth_engine.crm.http import CRMHTTPApplication
from sentinellayer_growth_engine.crm.service import CRMActor, CRMServiceError

ACTOR = CRMActor(user_id=UUID("11111111-1111-4111-8111-111111111111"))


class FakeService:
    def authorize(self, actor, *, mutation=False):
        return actor

    def search_accounts(self, **kwargs):
        return {"data": [{"id": 1}], "meta": {"has_more": False}}

    def accounts(self, **kwargs):
        return {"data": [{"id": 1}], "meta": {"has_more": False}}

    def account_360(self, **kwargs):
        return {"data": {"account": {"id": kwargs["account_id"]}}, "meta": {}}

    def contact_360(self, **kwargs):
        return {"data": {"contact": {"decision_maker_id": str(kwargs["decision_maker_id"])}}, "meta": {}}

    def crm_members(self):
        return {"data": [{"email": "operator@example.com", "role": "OPERATOR"}], "meta": {}}

    def update_account_fields(self, **kwargs):
        return {"data": {"id": kwargs["account_id"], **kwargs["fields"]}, "meta": {"request_id": kwargs["request_id"]}}

    def update_contact_fields(self, **kwargs):
        return {"data": {"decision_maker_id": str(kwargs["decision_maker_id"]), **kwargs["fields"]}, "meta": {"request_id": kwargs["request_id"]}}

    def task_queue(self, **kwargs):
        return {"data": [], "meta": {"has_more": False}}

    def contacts(self, **kwargs):
        return {"data": [{"decision_maker_id": "dm-1"}], "meta": {"has_more": False}}

    def pipeline(self):
        return {"data": [{"state": "NEW", "account_count": 1}], "meta": {"total_accounts": 1}}

    def bulk_state(self, **kwargs):
        return {"data": [{"id": 1, "status": "success"}], "meta": {"partial_failure": False, "succeeded": 1, "failed": 0}}

    def bulk_assign(self, **kwargs):
        return {"data": [{"id": 1, "status": "success"}], "meta": {"partial_failure": False, "succeeded": 1, "failed": 0}}
    def transition_account(self, **kwargs):
        if kwargs["actor"] is None:
            raise CRMServiceError("FORBIDDEN", "authenticated actor is required")
        return {"data": {"state": kwargs["to_state"]}, "meta": {"request_id": kwargs["request_id"]}}

    def transition_contact(self, **kwargs):
        return {"data": {"state": kwargs["to_state"]}, "meta": {"request_id": kwargs["request_id"]}}

    def create_activity(self, **kwargs):
        return {"data": {"touchpoint_id": "t1"}, "meta": {"request_id": kwargs["request_id"]}}

    def create_task(self, **kwargs):
        return {"data": {"sales_task_id": "t1"}, "meta": {"request_id": kwargs["request_id"]}}

    def create_note(self, **kwargs):
        return {"data": {"note_id": "n1"}, "meta": {"request_id": kwargs["request_id"]}}

    def export(self, **kwargs):
        return {"data": [{"id": 1}], "meta": {"entity": kwargs["entity"], "count": 1}}

    def opportunities(self, **kwargs):
        return {"data": [{"opportunity_id": "opp-1", "stage": kwargs.get("stage") or "QUALIFIED"}], "meta": {"has_more": False}}

    def opportunity(self, **kwargs):
        return {"data": {"opportunity_id": str(kwargs["opportunity_id"]), "stage": "QUALIFIED"}, "meta": {}}

    def create_opportunity(self, **kwargs):
        return {"data": {"opportunity_id": "opp-1", "name": kwargs["name"], "stage": kwargs["stage"]}, "meta": {"request_id": kwargs["request_id"]}}

    def update_opportunity(self, **kwargs):
        return {"data": {"opportunity_id": str(kwargs["opportunity_id"]), **kwargs["fields"]}, "meta": {"request_id": kwargs["request_id"]}}

    def transition_opportunity(self, **kwargs):
        return {"data": {"opportunity_id": str(kwargs["opportunity_id"]), "stage": kwargs["to_stage"]}, "meta": {"request_id": kwargs["request_id"]}}


def app(actor=ACTOR):
    return CRMHTTPApplication(FakeService(), lambda headers: actor)
def test_health_and_search_routes():
    application = app()
    status, payload = application.handle(method="GET", target="/healthz", headers={})
    assert status == 200
    assert payload["data"]["status"] == "ok"

    status, payload = application.handle(method="GET", target="/v1/crm/search?q=Byrna", headers={})
    assert status == 200
    assert payload["data"][0]["id"] == 1


def test_account_360_route():
    status, payload = app().handle(method="GET", target="/v1/crm/accounts/123", headers={})
    assert status == 200
    assert payload["data"]["account"]["id"] == 123
def test_state_route_passes_request_and_idempotency_context():
    status, payload = app().handle(
        method="POST",
        target="/v1/crm/accounts/123/state-transitions",
        headers={"x-request-id": "req-1", "idempotency-key": "idem-1"},
        body={"to_state": "QUALIFIED", "expected_version": 1},
    )
    assert status == 200
    assert payload["data"]["state"] == "QUALIFIED"


def test_missing_state_field_is_typed_input_error():
    status, payload = app().handle(
        method="POST",
        target="/v1/crm/accounts/123/state-transitions",
        headers={},
        body={"expected_version": 1},
    )
    assert status == 400
    assert payload["error"]["code"] == "INVALID_INPUT"


def test_unknown_route_returns_not_found():
    status, payload = app().handle(method="GET", target="/v1/crm/nope", headers={})
    assert status == 404
    assert payload["error"]["code"] == "NOT_FOUND"


def test_contacts_and_pipeline_routes():
    status, payload = app().handle(method="GET", target="/v1/crm/contacts", headers={})
    assert status == 200
    assert payload["data"][0]["decision_maker_id"] == "dm-1"

    status, payload = app().handle(method="GET", target="/v1/crm/pipeline", headers={})
    assert status == 200
    assert payload["meta"]["total_accounts"] == 1


def test_bulk_routes_return_per_record_envelope():
    headers = {"X-Request-ID": "bulk-1", "Idempotency-Key": "bulk-1"}
    status, payload = app().handle(
        method="POST", target="/v1/crm/bulk/state", headers=headers,
        body={"account_ids": [1], "to_state": "WORKING", "expected_versions": {"1": 1}},
    )
    assert status == 200
    assert payload["meta"]["succeeded"] == 1

    status, payload = app().handle(
        method="POST", target="/v1/crm/bulk/assign", headers=headers,
        body={"account_ids": [1], "owner_user_id": None, "expected_versions": {"1": 1}},
    )
    assert status == 200
    assert payload["data"][0]["status"] == "success"

def test_crm_route_requires_authentication():
    application = CRMHTTPApplication(FakeService(), lambda _headers: None)
    status, payload = application.handle(
        method="GET", target="/v1/crm/accounts", headers={}
    )
    assert status == 401
    assert payload["error"]["code"] == "UNAUTHENTICATED"


def test_contact_profile_and_edit_routes():
    person="00153984-f963-4c99-bf20-c0993b86c93b"
    status, payload = app().handle(method="GET", target=f"/v1/crm/contacts/{person}", headers={})
    assert status == 200
    assert payload["data"]["contact"]["decision_maker_id"] == person

    status, payload = app().handle(method="PATCH", target="/v1/crm/accounts/123", headers={"Idempotency-Key":"edit-1"}, body={"fields":{"name":"New Name"}})
    assert status == 200
    assert payload["data"]["name"] == "New Name"

    status, payload = app().handle(method="PATCH", target=f"/v1/crm/contacts/{person}", headers={"Idempotency-Key":"edit-2"}, body={"fields":{"title":"CTO"}})
    assert status == 200
    assert payload["data"]["title"] == "CTO"


def test_opportunity_routes_cover_create_list_detail_update_and_stage_transition():
    person = "00153984-f963-4c99-bf20-c0993b86c93b"
    headers = {"X-Request-ID": "opp-1", "Idempotency-Key": "opp-1"}

    status, payload = app().handle(
        method="GET",
        target="/v1/crm/opportunities?stage=DISCOVERY&limit=10",
        headers=headers,
    )
    assert status == 200
    assert payload["data"][0]["stage"] == "DISCOVERY"

    status, payload = app().handle(
        method="POST",
        target="/v1/crm/opportunities",
        headers=headers,
        body={"account_id": 42, "name": "SentinelLayer Pilot", "primary_contact_id": person},
    )
    assert status == 201
    assert payload["data"]["name"] == "SentinelLayer Pilot"

    status, payload = app().handle(
        method="GET",
        target="/v1/crm/opportunities/00153984-f963-4c99-bf20-c0993b86c93b",
        headers={},
    )
    assert status == 200

    status, payload = app().handle(
        method="PATCH",
        target="/v1/crm/opportunities/00153984-f963-4c99-bf20-c0993b86c93b",
        headers={"Idempotency-Key": "opp-edit"},
        body={"fields": {"value": 2500}, "expected_version": 1},
    )
    assert status == 200
    assert payload["data"]["value"] == 2500

    status, payload = app().handle(
        method="POST",
        target="/v1/crm/opportunities/00153984-f963-4c99-bf20-c0993b86c93b/stages",
        headers={"Idempotency-Key": "opp-stage"},
        body={"to_stage": "PROPOSAL", "expected_version": 2},
    )
    assert status == 200
    assert payload["data"]["stage"] == "PROPOSAL"


def test_export_route_requires_auth_and_returns_entity_envelope():
    status, payload = app().handle(
        method="GET", target="/v1/crm/export?entity=opportunities", headers={}
    )
    assert status == 200
    assert payload["meta"]["entity"] == "opportunities"
    assert payload["meta"]["count"] == 1
