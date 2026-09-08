# ruff: noqa: I001
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Channel = Literal["email", "linkedin", "instagram", "reddit", "social_content", "phone", "none"]


@dataclass(frozen=True)
class Recommendation:
    recommendation_type: str
    recommended_channel: Channel
    reason: str
    sequence: tuple[Channel, ...]
    confidence: float = 0.75
    requires_approval: bool = True


def recommend_next_action(
    *,
    priority: str,
    has_conversation: bool,
    awaiting_reply: bool,
    available_channels: list[Channel],
    social_warming_available: bool,
) -> Recommendation:
    channels = set(available_channels)

    if has_conversation:
        return Recommendation(
            recommendation_type="conversation_followup",
            recommended_channel="email" if "email" in channels else "none",
            reason="Conversation is active; keep the next action in the approved conversational sequence.",
            sequence=(("email",) if "email" in channels else ()),
            confidence=0.9,
        )

    if awaiting_reply:
        return Recommendation(
            recommendation_type="follow_up",
            recommended_channel="linkedin" if "linkedin" in channels else "email" if "email" in channels else "none",
            reason="No conversation has started on the current contact yet; recommend the next available approved touchpoint.",
            sequence=tuple(
                channel
                for channel in ("linkedin", "email", "instagram", "reddit")
                if channel in channels
            )[:2],
            confidence=0.8,
        )

    if social_warming_available and "linkedin" in channels and priority == "P1":
        return Recommendation(
            recommendation_type="optional_warm",
            recommended_channel="social_content",
            reason="A relevant social warming opportunity exists; warming is optional and does not block direct outreach.",
            sequence=("social_content", "linkedin", "email"),
            confidence=0.72,
        )

    if "email" in channels:
        return Recommendation(
            recommendation_type="initial_outreach",
            recommended_channel="email",
            reason="Email is the currently supported automated channel after operator sequence approval.",
            sequence=("email",),
            confidence=0.82,
        )

    return Recommendation(
        recommendation_type="operator_action",
        recommended_channel="none",
        reason="No automated channel is available; create an operator task.",
        sequence=(),
        confidence=0.7,
    )
