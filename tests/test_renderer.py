from datetime import datetime, timezone

import pytest

from sentinellayer_growth_engine.renderer import RenderContext, TreatmentRenderer, TreatmentRenderingError

UUIDS = {
    "enrollment": "11111111-1111-4111-8111-111111111111",
    "campaign": "22222222-2222-4222-8222-222222222222",
    "strategy": "33333333-3333-4333-8333-333333333333",
    "offer": "44444444-4444-4444-8444-444444444444",
    "message": "55555555-5555-4555-8555-555555555555",
    "cta": "66666666-6666-4666-8666-666666666666",
    "sequence": "77777777-7777-4777-8777-777777777777",
    "step": "88888888-8888-4888-8888-888888888888",
}

SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["schema_version","enrollment_id","campaign_id","person_id","account_id",
                 "sequence_step_id","strategy_version_id","offer_version_id","message_version_id",
                 "cta_version_id","sequence_version_id","recipient_email","subject","body_text",
                 "headers","rendered_at"],
    "properties": {
        "schema_version":{"type":"string"},
        "enrollment_id":{"type":"string","format":"uuid"},
        "campaign_id":{"type":"string","format":"uuid"},
        "sequence_step_id":{"type":"string","format":"uuid"},
        "strategy_version_id":{"type":"string","format":"uuid"},
        "offer_version_id":{"type":"string","format":"uuid"},
        "message_version_id":{"type":"string","format":"uuid"},
        "cta_version_id":{"type":"string","format":"uuid"},
        "sequence_version_id":{"type":"string","format":"uuid"},
        "person_id":{"type":"string"},
        "account_id":{"type":"string"},
        "recipient_email":{"type":"string","format":"email"},
        "subject":{"type":"string","minLength":1},
        "body_text":{"type":"string","minLength":1},
        "headers":{"type":"object"},
        "rendered_at":{"type":"string","format":"date-time"},
    },
}

def renderer():
    return TreatmentRenderer(SCHEMA)

def context(**kw):
    data=dict(enrollment_id=UUIDS["enrollment"], campaign_id=UUIDS["campaign"],
              person_id="p1", account_id="a1", recipient_email="buyer@example.com",
              strategy_version_id=UUIDS["strategy"], offer_version_id=UUIDS["offer"],
              sequence_version_id=UUIDS["sequence"], personalization={"first_name":"Sam"},
              evidence={"trigger":"recent release"})
    data.update(kw)
    return RenderContext(**data)

def versions(**kw):
    base={
        "strategy_version":{"id":UUIDS["strategy"],"status":"active"},
        "offer_version":{"id":UUIDS["offer"],"status":"active"},
        "message_version":{"id":UUIDS["message"],"status":"active",
                           "subject_template":"Quick question, {first_name}",
                           "body_template":"Hi {first_name},\n\nI noticed the trigger.\n\n{cta}",
                           "required_evidence":["trigger"]},
        "cta_version":{"id":UUIDS["cta"],"status":"active",
                       "wording_template":"Worth a quick reply?"},
        "sequence_step":{"id":UUIDS["step"],"sequence_version_id":UUIDS["sequence"],"asset_policy":"none"},
    }
    base.update(kw)
    return base

def test_renders_schema_valid_treatment():
    now=datetime(2026,9,2,12,0,tzinfo=timezone.utc)
    result=renderer().render(context=context(), **versions(), rendered_at=now)
    assert result["subject"] == "Quick question, Sam"
    assert "Worth a quick reply?" in result["body_text"]
    assert result["message_version_id"] == UUIDS["message"]

def test_missing_variable_fails():
    with pytest.raises(TreatmentRenderingError, match="unresolved variable"):
        renderer().render(context=context(personalization={}), **versions())

def test_missing_required_evidence_fails():
    with pytest.raises(TreatmentRenderingError, match="required evidence missing"):
        renderer().render(context=context(evidence={}), **versions())

def test_non_renderable_message_fails():
    message=dict(versions()["message_version"], status="draft")
    with pytest.raises(TreatmentRenderingError, match="message version is not renderable"):
        renderer().render(context=context(), **versions(message_version=message))

def test_wrong_sequence_step_fails():
    step=dict(versions()["sequence_step"], sequence_version_id="99999999-9999-4999-8999-999999999999")
    with pytest.raises(TreatmentRenderingError, match="sequence step/version mismatch"):
        renderer().render(context=context(), **versions(sequence_step=step))

def test_asset_policy_is_enforced():
    with pytest.raises(TreatmentRenderingError, match="asset supplied"):
        renderer().render(context=context(), **versions(),
                            asset={"type":"loom","url":"https://example.test/x"})

def test_recipient_is_not_template_mutated():
    result=renderer().render(context=context(), **versions())
    assert result["recipient_email"] == "buyer@example.com"
