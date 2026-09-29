from uuid import UUID

import pytest

from sentinellayer_growth_engine.crm.http import CRMHTTPApplication
from sentinellayer_growth_engine.crm.service import CRMActor, CRMServiceError

ACTOR = CRMActor(user_id=UUID("11111111-1111-4111-8111-111111111111"))


class FakeService:
    def search_accounts(self, **kwargs):
        return {"data": [{"id": 1}], "meta": {"has_more": False}}

    def accounts(self, **kwargs):
        return {"data": [{"id": 1}], "meta": {"has_more": False}}

    def account_360(self, **kwargs):
        return {"data": {"account": {"id": kwargs["account_id"]}}, "meta": {}}

    def task_queue(self, **kwargs):
        return {"data": [], "meta": {"has_more": False}}

    def contacts(self, **kwargs):
        return {"data": [{"decision_maker_id": "dm-1"}], "meta": {"has_more": False}}

    def pipeline(self):
        return {"data": [{"state": "NEW", "account_count": 1}], "meta": {"total_accounts": 1}}
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
