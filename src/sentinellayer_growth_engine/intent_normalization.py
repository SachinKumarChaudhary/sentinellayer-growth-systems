from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from .intelligence_scoring import COMPLIANCE_INTENT, INTENT_RULES, IntentSignalInput


class IntentSignalNormalizationError(ValueError):
    """Raised when a research signal cannot be mapped to a canonical playbook signal."""


@dataclass(frozen=True)
class NormalizedIntentSignal:
    signal_type: str
    signal_date: date
    weight: float
    half_life_days: int

    def as_score_input(self) -> IntentSignalInput:
        return IntentSignalInput(
            signal_type=self.signal_type,
            signal_date=self.signal_date,
            weight=self.weight,
            half_life_days=self.half_life_days,
        )


ALIASES: dict[str, tuple[str, ...]] = {
    "funding": ("funding", "funding round", "raise", "raised", "investment", "capital raise", "scale milestone", "major acquisition of scale"),
    "new_c_suite": ("new c-suite", "new c suite", "executive hire", "exec hire", "new ceo", "new cfo", "new ctoo", "new cto", "new cpo", "new cmo", "new ciso"),
    "security_hiring": ("security hiring", "security hire", "security engineer", "cloud security", "risk analyst", "fraud analyst", "trust and safety hiring", "trust & safety hiring", "fraud hiring", "risk hiring", "data security hiring", "hiring spike"),
    "tech_migration": ("tech migration", "technology migration", "replatform", "replatforming", "platform migration", "technology rollout", "new technology stack", "improving our technology"),
    "competitor_mention": ("competitor mention", "sift", "seon", "forter", "kount", "castle", "arkose"),
    "dark_funnel": ("dark-funnel", "dark funnel", "reddit complaint", "community complaint", "fraud complaint", "ato complaint", "account takeover complaint", "scalper complaint", "payout complaint", "chargeback complaint"),
    "seasonal_window": ("seasonal window", "seasonal spike", "seasonal trigger"),
    "franchise_launch": ("franchise launch", "first franchise", "new franchise", "location launch", "store opening", "new store"),
    "new_market": ("new market", "market entry", "market expansion", "international expansion", "eu launch", "expanded to"),
    "regulated_expansion": ("regulated expansion", "regulated category", "new regulated category", "new compliance regime", "health claims expansion"),
    "award": ("award", "recognition milestone", "future50", "inc 5000", "forbes feature"),
    "pricing_visit": ("pricing visit", "pricing page visit", "pricing page"),
    "trial_install": ("trial install", "sdk installed", "evaluate calls", "pql"),
    "docs_visit": ("docs visit", "documentation visit", "docs page visit"),
    "pci": ("pci", "pci dss", "pci dss 4.0", "pci 4.0"),
    "ca_breach": ("ca breach", "california breach", "sb 362", "30-day breach"),
    "ftc_click_to_cancel": ("ftc click-to-cancel", "click-to-cancel", "click to cancel"),
    "dpdp": ("dpdp", "dpdp act", "digital personal data protection"),
    "gdpr": ("gdpr", "gdpr art. 32", "gdpr article 32"),
    "soc2_requirement": ("soc2 requirement", "soc 2 requirement", "soc2 procurement", "vendor security review"),
}


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _contains_alias(normalized: str, alias: str) -> bool:
    """Match aliases as words/phrases, avoiding accidental substring matches."""
    pattern = rf"(?<![a-z0-9]){re.escape(_normalize_text(alias))}(?![a-z0-9])"
    return re.search(pattern, normalized) is not None


def normalize_signal_type(signal_type: str) -> str:
    normalized = _normalize_text(signal_type)
    if not normalized:
        raise IntentSignalNormalizationError("signal_type cannot be empty")
    if normalized in INTENT_RULES or normalized in COMPLIANCE_INTENT:
        return normalized

    matches = [
        canonical
        for canonical, aliases in ALIASES.items()
        if any(_contains_alias(normalized, alias) for alias in aliases)
    ]
    unique_matches = sorted(set(matches))
    if not unique_matches:
        raise IntentSignalNormalizationError(f"unsupported intent signal type: {signal_type!r}")
    if len(unique_matches) > 1:
        raise IntentSignalNormalizationError(
            f"ambiguous intent signal type {signal_type!r}: {unique_matches}"
        )
    return unique_matches[0]


def normalize_signal(*, signal_type: str, signal_date: date) -> NormalizedIntentSignal:
    canonical = normalize_signal_type(signal_type)
    weight, half_life_days = {**INTENT_RULES, **COMPLIANCE_INTENT}[canonical]
    return NormalizedIntentSignal(
        signal_type=canonical,
        signal_date=signal_date,
        weight=weight,
        half_life_days=half_life_days,
    )


def normalize_signals(signals: list[tuple[str, date]]) -> list[IntentSignalInput]:
    """Convert raw research labels to deterministic v2.1 scoring inputs."""
    return [
        normalize_signal(signal_type=signal_type, signal_date=signal_date).as_score_input()
        for signal_type, signal_date in signals
    ]
