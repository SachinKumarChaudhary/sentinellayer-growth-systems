from __future__ import annotations

from typing import Any

SAFE_STOP_CLASSIFICATIONS = {"unsubscribe", "negative"}
DEFER_CLASSIFICATIONS = {"not_now", "ooo"}
POSITIVE_CLASSIFICATIONS = {"interested", "question"}


def reconcile_conversation_analysis(
    *,
    deterministic_classification: str,
    analysis: dict[str, Any] | None,
) -> dict[str, Any]:
    """Reconcile model enrichment with deterministic safety decisions.

    The semantic model may enrich an inbound reply, but it cannot override an
    explicit opt-out or a deterministic stop/defer classification.
    """
    if deterministic_classification in SAFE_STOP_CLASSIFICATIONS:
        return {
            "effective_intent": deterministic_classification,
            "action": "suppress_contact" if deterministic_classification == "unsubscribe" else "stop_cold_sequence",
            "send_allowed": False,
            "reason": "deterministic_safety_precedence",
        }

    if deterministic_classification in DEFER_CLASSIFICATIONS:
        return {
            "effective_intent": deterministic_classification,
            "action": "schedule_later" if deterministic_classification == "not_now" else "defer_until_return",
            "send_allowed": False,
            "reason": "deterministic_defer_precedence",
        }

    if not analysis:
        return {
            "effective_intent": deterministic_classification,
            "action": "human_follow_up" if deterministic_classification in POSITIVE_CLASSIFICATIONS else "human_review",
            "send_allowed": deterministic_classification in POSITIVE_CLASSIFICATIONS,
            "reason": "semantic_analysis_unavailable",
        }

    if bool(analysis.get("explicit_opt_out")):
        return {
            "effective_intent": "unsubscribe",
            "action": "suppress_contact",
            "send_allowed": False,
            "reason": "semantic_explicit_opt_out",
        }

    primary = analysis.get("primary_intent")
    if primary in SAFE_STOP_CLASSIFICATIONS:
        return {
            "effective_intent": str(primary),
            "action": "suppress_contact" if primary == "unsubscribe" else "stop_cold_sequence",
            "send_allowed": False,
            "reason": "semantic_safety_precedence",
        }

    if primary in DEFER_CLASSIFICATIONS:
        return {
            "effective_intent": str(primary),
            "action": "schedule_later" if primary == "not_now" else "defer_until_return",
            "send_allowed": False,
            "reason": "semantic_defer_precedence",
        }

    if primary in POSITIVE_CLASSIFICATIONS or deterministic_classification in POSITIVE_CLASSIFICATIONS:
        return {
            "effective_intent": str(primary or deterministic_classification),
            "action": "human_follow_up",
            "send_allowed": True,
            "reason": "positive_intent_reconciled",
        }

    return {
        "effective_intent": str(primary or deterministic_classification),
        "action": "human_review",
        "send_allowed": False,
        "reason": "no_safe_automatic_action",
    }
