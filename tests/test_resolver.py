import pytest

from sentinellayer_growth_engine.resolver import (
    CampaignResolutionError,
    ResolutionContext,
    assign_variant,
    resolve_treatment,
    select_sequence_step,
)


def ctx(**overrides):
    values = {
        "campaign_id": "campaign-1",
        "person_id": "person-1",
        "priority": "P1",
        "active_strategy_version_id": "strategy-1",
        "active_offer_version_id": "offer-1",
        "active_sequence_version_id": "sequence-1",
        "experiment_id": None,
    }
    values.update(overrides)
    return ResolutionContext(**values)


def version(version_id):
    return {"id": version_id, "status": "active"}


def test_resolver_returns_frozen_base_treatment():
    result = resolve_treatment(
        context=ctx(),
        strategy_version=version("strategy-1"),
        offer_version=version("offer-1"),
        sequence_version=version("sequence-1"),
    )
    assert result.strategy_version_id == "strategy-1"
    assert result.offer_version_id == "offer-1"
    assert result.sequence_version_id == "sequence-1"


def test_variant_assignment_is_stable():
    variants = [{"id": "A", "allocation_pct": 50}, {"id": "B", "allocation_pct": 50}]
    assert assign_variant(campaign_id="c", person_id="p", variants=variants) == assign_variant(
        campaign_id="c", person_id="p", variants=variants
    )


def test_experiment_can_override_treatment_versions():
    result = resolve_treatment(
        context=ctx(experiment_id="exp-1"),
        strategy_version=version("strategy-1"),
        offer_version=version("offer-1"),
        sequence_version=version("sequence-1"),
        experiment={"id": "exp-1", "status": "running"},
        experiment_variants=[{
            "id": "variant-b",
            "allocation_pct": 100,
            "strategy_version_id": "strategy-2",
            "offer_version_id": "offer-2",
            "sequence_version_id": "sequence-2",
        }],
    )
    assert result.strategy_version_id == "strategy-2"
    assert result.offer_version_id == "offer-2"
    assert result.sequence_version_id == "sequence-2"


def test_allocation_overflow_fails_closed():
    with pytest.raises(CampaignResolutionError, match="exceed"):
        assign_variant(campaign_id="c", person_id="p", variants=[
            {"id": "A", "allocation_pct": 60},
            {"id": "B", "allocation_pct": 50},
        ])


def test_inactive_version_fails_closed():
    with pytest.raises(CampaignResolutionError, match="not renderable"):
        resolve_treatment(
            context=ctx(),
            strategy_version={"id": "strategy-1", "status": "retired"},
            offer_version=version("offer-1"),
            sequence_version=version("sequence-1"),
        )


def test_step_selection_is_version_bound():
    steps = [
        {"id": "old-step", "sequence_version_id": "old", "step_no": 1, "active": True},
        {"id": "new-step", "sequence_version_id": "sequence-1", "step_no": 1, "active": True},
    ]
    assert select_sequence_step(
        sequence_steps=steps, sequence_version_id="sequence-1", step_no=1
    )["id"] == "new-step"


def test_duplicate_active_steps_fail_closed():
    steps = [
        {"id": "a", "sequence_version_id": "sequence-1", "step_no": 1, "active": True},
        {"id": "b", "sequence_version_id": "sequence-1", "step_no": 1, "active": True},
    ]
    with pytest.raises(CampaignResolutionError, match="exactly one"):
        select_sequence_step(sequence_steps=steps, sequence_version_id="sequence-1", step_no=1)
