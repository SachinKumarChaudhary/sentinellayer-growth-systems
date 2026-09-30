from uuid import UUID, uuid4

import pytest

from sentinellayer_growth_engine.crm.service import CRMActor, CRMService, CRMServiceError


ACTOR = CRMActor(user_id=UUID("11111111-1111-4111-8111-111111111111"))


class ReadRepo:
    def list_accounts(self, **kwargs):
        return {"data": [{"id": 1}], "meta": {"has_more": False}}

    def search_accounts(self, **kwargs):
        return [{"id": 1}]

    def get_account_360(self, **kwargs):
        return {"account": {"id": kwargs["account_id"]}}

    def get_contact_360(self, **kwargs):
        return {"contact": {"decision_maker_id": str(kwargs["decision_maker_id"])}}

    def list_contacts(self, **kwargs):
        return {"data": [{"decision_maker_id": "dm-1"}], "meta": {"has_more": False}}

    def pipeline_summary(self):
        return {"data": [{"state": "NEW", "account_count": 1}], "meta": {"total_accounts": 1}}


class WriteRepo:
    def get_user_access(self, **kwargs):
        return {"user_id": kwargs["user_id"], "role": "OPERATOR", "active": True}

    def update_account_fields(self, **kwargs):
        return {"id": kwargs["account_id"], **kwargs["fields"]}

    def update_contact_fields(self, **kwargs):
        return {"decision_maker_id": str(kwargs["decision_maker_id"]), **kwargs["fields"]}

    def list_crm_members(self):
        return [{"user_id": str(ACTOR.user_id), "email": "operator@example.com", "role": "OPERATOR", "active": True}]
    def initialize_account_state(self, **kwargs):
        return {"account_id": kwargs["account_id"], "state": "NEW"}

    def transition_account_state(self, **kwargs):
        return {"account_id": kwargs["account_id"], "state": kwargs["to_state"], "version": 2}

    def transition_contact_state(self, **kwargs):
        return {"decision_maker_id": str(kwargs["decision_maker_id"]), "state": kwargs["to_state"]}

    def create_note(self, **kwargs):
        return {"note_id": "note-1"}

    def create_manual_activity(self, **kwargs):
        return {"touchpoint_id": "touch-1"}

    def create_task(self, **kwargs):
        return {"sales_task_id": "task-1"}

    def export_records(self, **kwargs):
        return [{"id": 1}]

    def list_opportunities(self, **kwargs):
        return [{"opportunity_id": "opp-1", "stage": kwargs.get("stage") or "QUALIFIED"}]

    def get_opportunity(self, **kwargs):
        return {"opportunity_id": str(kwargs["opportunity_id"]), "stage": "QUALIFIED"}

    def create_opportunity(self, **kwargs):
        return {"opportunity_id": "opp-1", "name": kwargs["name"], "stage": kwargs["stage"]}

    def update_opportunity(self, **kwargs):
        return {"opportunity_id": str(kwargs["opportunity_id"]), **kwargs["fields"]}

    def transition_opportunity(self, **kwargs):
        return {"opportunity_id": str(kwargs["opportunity_id"]), "stage": kwargs["to_stage"]}

    def list_task_queue(self, **kwargs):
        return [{"sales_task_id": "task-1"}]

    def bulk_transition_accounts(self, **kwargs):
        return [
            {"id": 1, "status": "success", "data": {"state": kwargs["to_state"]}},
            {"id": 2, "status": "failed", "error": "version conflict"},
        ]

    def bulk_assign_accounts(self, **kwargs):
        return [
            {"id": 1, "status": "success", "data": {"owner_user_id": "u"}},
            {"id": 2, "status": "failed", "error": "forbidden"},
        ]

def service() -> CRMService:
    return CRMService(write_repo=WriteRepo(), read_repo=ReadRepo())


def test_actor_required_for_mutation():
    with pytest.raises(CRMServiceError) as exc:
        service().initialize_account(account_id=1, actor=None)
    assert exc.value.code == "FORBIDDEN"


def test_account_read_models_are_wrapped():
    assert service().accounts()["data"][0]["id"] == 1
    assert service().search_accounts(query="alpha")["data"][0]["id"] == 1
    assert service().account_360(account_id=1)["data"]["account"]["id"] == 1


def test_state_mutation_preserves_actor_context():
    result = service().transition_account(
        account_id=1,
        to_state="QUALIFIED",
        expected_version=1,
        actor=ACTOR,
        request_id="req-1",
        idempotency_key="idem-1",
    )
    assert result["data"]["state"] == "QUALIFIED"


def test_contact_transition_uses_uuid():
    result = service().transition_contact(
        decision_maker_id=uuid4(),
        to_state="REPLIED",
        expected_version=1,
        actor=ACTOR,
    )
    assert result["data"]["state"] == "REPLIED"


def test_contacts_and_pipeline():
    assert service().contacts()["data"][0]["decision_maker_id"] == "dm-1"
    assert service().pipeline()["meta"]["total_accounts"] == 1


def test_bulk_operations_return_per_record_results():
    write = WriteRepo()
    service_obj = CRMService(write_repo=write, read_repo=ReadRepo())
    state = service_obj.bulk_state(
        account_ids=[1,2], to_state="WORKING",
        expected_versions={1:1,2:1}, actor=ACTOR,
        idempotency_key="bulk-1",
    )
    assert state["meta"]["partial_failure"] is True
    assert state["meta"]["succeeded"] == 1
    assigned = service_obj.bulk_assign(
        account_ids=[1,2], owner_user_id=None,
        expected_versions={1:1,2:1}, actor=ACTOR,
    )
    assert assigned["meta"]["failed"] == 1


def test_opportunity_and_export_services_are_exposed():
    obj = service()
    opportunity_id = uuid4()
    assert obj.export(entity="opportunities", actor=ACTOR)["data"][0]["id"] == 1
    assert obj.opportunities(stage="DISCOVERY")["data"][0]["stage"] == "DISCOVERY"
    assert obj.opportunity(opportunity_id=opportunity_id)["data"]["opportunity_id"] == str(opportunity_id)
    created = obj.create_opportunity(
        account_id=1, name="Pilot", owner_user_id=ACTOR.user_id, actor=ACTOR,
        stage="QUALIFIED", request_id="opp-create", idempotency_key="opp-create",
    )
    assert created["data"]["name"] == "Pilot"
    updated = obj.update_opportunity(
        opportunity_id=opportunity_id, fields={"value": 100}, expected_version=1,
        actor=ACTOR,
    )
    assert updated["data"]["value"] == 100
    moved = obj.transition_opportunity(
        opportunity_id=opportunity_id, to_stage="DISCOVERY", expected_version=2,
        actor=ACTOR,
    )
    assert moved["data"]["stage"] == "DISCOVERY"


def test_account_and_contact_profile_mutations_are_exposed():
    obj=service()
    assert obj.update_account_fields(account_id=1, fields={"name":"Acme"}, actor=ACTOR)["data"]["name"] == "Acme"
    assert obj.update_contact_fields(decision_maker_id=uuid4(), fields={"title":"CTO"}, actor=ACTOR)["data"]["title"] == "CTO"
    assert obj.contact_360(decision_maker_id=uuid4())["data"]["contact"]["decision_maker_id"]
    assert obj.crm_members()["data"][0]["role"] == "OPERATOR"
