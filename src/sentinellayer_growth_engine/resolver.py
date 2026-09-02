from collections.abc import Mapping
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, , Sequence


class CampaignResolutionError(ValueError):
    """Raised when a campaign cannot produce a safe treatment."""


@dataclass(frozen=True)
class TreatmentSelection:
    strategy_version_id: str
    offer_version_id: str | None
    sequence_version_id: str
    experiment_id: str | None
    experiment_variant_id: str | None


@dataclass(frozen=True)
class ResolutionContext:
    campaign_id: str
    person_id: str
    priority: str
    active_strategy_version_id: str
    active_offer_version_id: str | None
    active_sequence_version_id: str
    experiment_id: str | None = None


def _stable_bucket(key: str) -> int:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % 10_000


def assign_variant(
    *,
    campaign_id: str,
    person_id: str,
    variants: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    """Assign one experiment variant deterministically using allocation_pct."""
    if not variants:
        return None
    total = 0.0
    normalized: list[tuple[float, Mapping[str, Any]]] = []
    for variant in variants:
        try:
            allocation = float(variant["allocation_pct"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CampaignResolutionError("experiment variant has invalid allocation_pct") from exc
        if allocation < 0 or allocation > 100:
            raise CampaignResolutionError("experiment allocation_pct must be between 0 and 100")
        total += allocation
        normalized.append((allocation, variant))
    if total > 100.000001:
        raise CampaignResolutionError("experiment allocations exceed 100%")
    bucket = _stable_bucket(f"{campaign_id}:{person_id}") / 100.0
    cursor = 0.0
    for allocation, variant in normalized:
        cursor += allocation
        if bucket < cursor:
            return variant
    return None


def _version_is_usable(record: Mapping[str, Any] | None, name: str) -> None:
    if record is None:
        raise CampaignResolutionError(f"{name} version is missing")
    if record.get("status") not in {"reviewed", "testing", "active"}:
        raise CampaignResolutionError(f"{name} version is not renderable")


def resolve_treatment(
    *,
    context: ResolutionContext,
    strategy_version: Mapping[str, Any],
    offer_version: Mapping[str, Any] | None,
    sequence_version: Mapping[str, Any],
    experiment: Mapping[str, Any] | None = None,
    experiment_variants: Sequence[Mapping[str, Any]] = (),
) -> TreatmentSelection:
    """Resolve a campaign treatment without rendering or sending mail."""
    if context.priority not in {"P1", "P2", "P3", "P4"}:
        raise CampaignResolutionError(f"unknown priority: {context.priority}")
    _version_is_usable(strategy_version, "strategy")
    _version_is_usable(sequence_version, "sequence")
    if offer_version is not None:
        _version_is_usable(offer_version, "offer")

    if strategy_version.get("id") != context.active_strategy_version_id:
        raise CampaignResolutionError("strategy context/version mismatch")
    if sequence_version.get("id") != context.active_sequence_version_id:
        raise CampaignResolutionError("sequence context/version mismatch")
    if offer_version is not None and offer_version.get("id") != context.active_offer_version_id:
        raise CampaignResolutionError("offer context/version mismatch")

    experiment_id = None
    variant_id = None
    selected_strategy = context.active_strategy_version_id
    selected_offer = context.active_offer_version_id
    selected_sequence = context.active_sequence_version_id

    if experiment is not None:
        if experiment.get("status") != "running":
            raise CampaignResolutionError("experiment is not running")
        if context.experiment_id != experiment.get("id"):
            raise CampaignResolutionError("experiment context/id mismatch")
        variant = assign_variant(
            campaign_id=context.campaign_id,
            person_id=context.person_id,
            variants=experiment_variants,
        )
        if variant is not None:
            variant_id = str(variant["id"])
            selected_strategy = str(variant.get("strategy_version_id") or selected_strategy)
            selected_offer = str(variant["offer_version_id"]) if variant.get("offer_version_id") else selected_offer
            selected_sequence = str(variant.get("sequence_version_id") or selected_sequence)
            experiment_id = str(experiment["id"])

    return TreatmentSelection(
        strategy_version_id=selected_strategy,
        offer_version_id=selected_offer,
        sequence_version_id=selected_sequence,
        experiment_id=experiment_id,
        experiment_variant_id=variant_id,
    )


def select_sequence_step(
    *,
    sequence_steps: Sequence[Mapping[str, Any]],
    sequence_version_id: str,
    step_no: int,
) -> Mapping[str, Any]:
    if step_no < 1:
        raise CampaignResolutionError("step_no must be >= 1")
    matches = [
        step for step in sequence_steps
        if step.get("sequence_version_id") == sequence_version_id
        and int(step.get("step_no", -1)) == step_no
        and bool(step.get("active", True))
    ]
    if len(matches) != 1:
        raise CampaignResolutionError(
            f"expected exactly one active step, found {len(matches)} for step {step_no}"
        )
    return matches[0]
