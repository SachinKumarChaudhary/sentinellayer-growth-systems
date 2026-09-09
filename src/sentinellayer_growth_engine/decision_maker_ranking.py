from __future__ import annotations

from dataclasses import dataclass

from .enrichment_contracts import DecisionMaker


@dataclass(frozen=True)
class RankedDecisionMaker:
    decision_maker: DecisionMaker
    score: float
    eligible: bool
    reason: str


CISO_TITLES = {
    "ciso",
    "chief information security officer",
    "chief information security & risk officer",
    "chief information security and risk officer",
}

ROLE_FAMILY_SCORES = {
    "security": 50,
    "identity": 48,
    "risk": 44,
    "fraud": 44,
    "engineering": 40,
    "product": 38,
    "compliance": 36,
    "technology": 34,
}


def _normalized_title(title: str | None) -> str:
    return " ".join((title or "").strip().lower().split())


def _role_score(decision_maker: DecisionMaker) -> float:
    family = (decision_maker.role_family or "").strip().lower()
    if family in ROLE_FAMILY_SCORES:
        return float(ROLE_FAMILY_SCORES[family])
    title = _normalized_title(decision_maker.title)
    for family_name, score in ROLE_FAMILY_SCORES.items():
        if family_name in title:
            return float(score - 4)
    return 20.0


def _seniority_score(title: str | None) -> float:
    normalized = _normalized_title(title)
    if any(token in normalized for token in ("chief ", "vp ", "vice president", "head of")):
        return 20.0
    if any(token in normalized for token in ("director", "avp", "general manager")):
        return 16.0
    if any(token in normalized for token in ("lead", "principal", "manager")):
        return 12.0
    return 8.0


def _verification_score(decision_maker: DecisionMaker) -> float:
    statuses = {contact.verification_status for contact in decision_maker.contacts}
    if "verified" in statuses:
        return 15.0
    if statuses and statuses.issubset({"unknown"}):
        return 3.0
    if statuses:
        return 6.0
    return 0.0


def rank_decision_makers(
    decision_makers: list[DecisionMaker],
    *,
    limit: int = 6,
) -> list[RankedDecisionMaker]:
    """Rank DMs for operator review; never treats ranking as outreach approval."""
    if limit < 1:
        raise ValueError("limit must be positive")

    ranked: list[RankedDecisionMaker] = []
    for decision_maker in decision_makers:
        score = _role_score(decision_maker)
        score += _seniority_score(decision_maker.title)
        score += _verification_score(decision_maker)
        score += (decision_maker.confidence or 0.0) * 5.0
        if decision_maker.role_priority is not None:
            score += max(0.0, 6.0 - min(decision_maker.role_priority, 6))

        title = _normalized_title(decision_maker.title)
        reason = "ranked_for_human_review"
        if title in CISO_TITLES:
            reason = "security_owner_priority"

        ranked.append(
            RankedDecisionMaker(
                decision_maker=decision_maker,
                score=round(score, 2),
                eligible=True,
                reason=reason,
            )
        )

    # The playbook makes an actual CISO a hard ordering rule, not merely a
    # scoring preference. Keep the normal score ordering for all other roles.
    ranked.sort(
        key=lambda item: (
            _normalized_title(item.decision_maker.title) in CISO_TITLES,
            item.score,
            item.decision_maker.role_priority is not None,
            -(item.decision_maker.role_priority or 999),
            item.decision_maker.full_name.lower(),
        ),
        reverse=True,
    )
    return ranked[:limit]
