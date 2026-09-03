import pytest

from sentinellayer_growth_engine.campaign import (
    CampaignRenderError,
    RenderContext,
    TreatmentRenderer,
)

def context(**overrides: object) -> RenderContext:
    values: dict[str, object] = {
        "enrollment_id": "00000000-0000-0000-0000-000000000001",
        "campaign_id": "00000000-0000-0000-0000-000000000002",
        "person_id": "1",
        "account_id": "account-1",
        "sequence_step_id": "00000000-0000-0000-0000-000000000003",
        "strategy_version_id": "00000000-0000-0000-0000-000000000004",
        "offer_version_id": "00000000-0000-0000-0000-000000000005",
        "message_version_id": "00000000-0000-0000-0000-000000000006",
        "cta_version_id": "00000000-0000-0000-0000-000000000007",
        "sequence_version_id": "00000000-0000-0000-0000-000000000008",
        "recipient_email": "buyer@example.com",
        "personalization": {"first_name": "Alex", "company": "Example"},
        "evidence": {"trigger": "new security initiative"},
    }
    values.update(overrides)
    return RenderContext(**values)  # type: ignore[arg-type]


MESSAGE = {
    "status": "active",
    "qa_status": "approved",
    "subject_template": "{{first_name}}, quick question about {{company}}",
    "body_template": "Hi {{first_name}},\n\nSaw {{company}}'s {{trigger}}.\n\n{{cta.label}}",
    "evidence_requirements": {"required": ["trigger"]},
}
CTA = {
    "status": "active",
    "label": "Worth comparing notes?",
    "action_type": "reply",
    "target": None,
}


def test_render_produces_valid_contract():
    result = TreatmentRenderer().render(
        context=context(),
        message_version=MESSAGE,
        cta_version=CTA,
    )
    assert result["subject"] == "Alex, quick question about Example"
    assert "Saw Example's new security initiative." in result["body_text"]
    assert result["message_version_id"] == "00000000-0000-0000-0000-000000000006"
    assert result["recipient_email"] == "buyer@example.com"


def test_missing_variable_fails_closed():
    with pytest.raises(CampaignRenderError, match="missing personalization variable"):
        TreatmentRenderer().render(
            context=context(personalization={"company": "Example"}),
            message_version=MESSAGE,
            cta_version=CTA,
        )


def test_missing_evidence_fails_closed():
    with pytest.raises(CampaignRenderError, match="required evidence missing"):
        TreatmentRenderer().render(
            context=context(evidence={}),
            message_version=MESSAGE,
            cta_version=CTA,
        )


def test_unapproved_message_cannot_render():
    with pytest.raises(CampaignRenderError, match="QA approved"):
        TreatmentRenderer().render(
            context=context(),
            message_version={**MESSAGE, "qa_status": "unreviewed"},
            cta_version=CTA,
        )


def test_retired_cta_cannot_render():
    with pytest.raises(CampaignRenderError, match="CTA version is not renderable"):
        TreatmentRenderer().render(
            context=context(),
            message_version=MESSAGE,
            cta_version={**CTA, "status": "retired"},
        )


def test_recipient_is_taken_from_frozen_context():
    result = TreatmentRenderer().render(
        context=context(recipient_email="decision-maker@example.com"),
        message_version=MESSAGE,
        cta_version=CTA,
    )
    assert result["recipient_email"] == "decision-maker@example.com"


def test_nested_personalization_and_cta_render():
    result = TreatmentRenderer().render(
        context=context(personalization={"first_name": "Sam", "company": "Acme", "contact": {"role": "CTO"}}),
        message_version={
            **MESSAGE,
            "subject_template": "{{contact.role}} at {{company}}",
            "body_template": "Hi {{first_name}},\n{{cta.label}}",
        },
        cta_version=CTA,
    )
    assert result["subject"] == "CTO at Acme"
    assert "Worth comparing notes?" in result["body_text"]
