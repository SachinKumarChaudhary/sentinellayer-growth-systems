from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from .intelligence_scoring import CONTEXT_ONLY_SIGNAL_TYPES, INTENT_RULES, IntentSignalInput


class IntentSignalNormalizationError(ValueError):
    """Raised when a research signal cannot be mapped to a canonical v3.4 signal."""


@dataclass(frozen=True)
class NormalizedIntentSignal:
    signal_type: str
    signal_date: date
    weight: float
    half_life_days: int
    dedupe_key: str | None = None

    def as_score_input(self) -> IntentSignalInput:
        return IntentSignalInput(
            signal_type=self.signal_type,
            signal_date=self.signal_date,
            weight=self.weight,
            half_life_days=self.half_life_days,
            dedupe_key=self.dedupe_key,
        )


# v3.4 intentionally keeps A1-A6 as research buckets while normalizing them
# into one canonical scored signal taxonomy.
ALIASES: dict[str, tuple[str, ...]] = {
    "funding": ("funding", "funding round", "raise", "raised", "investment", "capital raise", "scale milestone", "major acquisition of scale"),
    "executive_business_event": ("new c-suite", "new c suite", "executive hire", "exec hire", "new ceo", "new cfo", "new cpo", "new cmo", "executive/business event", "business event"),
    "new_security_leader": ("new cto", "new ciso", "new cio", "new security leader", "security leader appointed", "head of security appointed"),
    "security_hiring": ("security hiring", "security hire", "security engineer", "application security", "cloud security", "risk analyst", "fraud analyst", "trust and safety hiring", "trust & safety hiring", "fraud hiring", "risk hiring", "data security hiring", "hiring spike", "security project"),
    "tech_migration": ("tech migration", "technology migration", "replatform", "replatforming", "platform migration", "authentication migration", "auth migration", "account-flow redesign", "payment architecture change", "major security-stack change", "improving our technology"),
    "competitor_evaluation": ("competitor evaluation", "tool comparison", "vendor evaluation", "replacement project", "incumbent dissatisfaction", "sift evaluation", "seon evaluation", "forter evaluation", "kount evaluation", "castle evaluation", "arkose evaluation", "signifyd evaluation", "datadome evaluation"),
    "explicit_incident": ("explicit company-specific incident", "company-specific ato", "company-specific account takeover", "compromised accounts", "confirmed account takeover", "session hijacking incident", "company-specific fraud incident"),
    "authenticated_product_change": ("authenticated product change", "new authenticated product capability", "new customer portal", "new account feature", "new app", "new administrative capability", "new subscription capability", "connected device launch that changes the authenticated surface"),
    "pricing_visit": ("pricing visit", "pricing page visit", "pricing engagement", "commercial evaluation"),
    "docs_visit": ("docs visit", "documentation visit", "docs page visit", "quickstart engagement", "api docs engagement", "sdk docs engagement", "proxy docs engagement"),
    "trial_install": ("trial install", "trial signup", "signup", "active evaluation"),
    "sdk_install": ("sdk installed", "deployment", "sdk deployment"),
    "evaluate_activity": ("evaluate calls", "/evaluate activity", "product qualified", "pql"),
    "new_market": ("new market", "market entry", "market expansion", "international expansion", "eu launch", "expanded to"),
    "regulated_expansion": ("regulated expansion", "regulated category", "new regulated category", "new compliance regime", "health claims expansion"),
    "franchise_launch": ("franchise launch", "first franchise", "new franchise", "location launch", "store opening", "new store"),
    "seasonal_window": ("seasonal window", "seasonal spike", "seasonal trigger"),
    "dark_funnel": ("dark-funnel", "dark funnel", "community complaint", "reddit complaint", "category discussion", "generic reddit complaint"),
    "pci": ("pci", "pci dss", "pci dss 4.0", "pci 4.0"),
    "ca_breach": ("ca breach", "california breach", "sb 362", "30-day breach"),
    "ftc_click_to_cancel": ("ftc click-to-cancel", "click-to-cancel", "click to cancel"),
    "dpdp": ("dpdp", "dpdp act", "digital personal data protection"),
    "gdpr": ("gdpr", "gdpr art. 32", "gdpr article 32"),
    "soc2_requirement": ("soc2 requirement", "soc 2 requirement", "soc2 procurement", "vendor security review"),
    "award": ("award", "recognition milestone", "future50", "inc 5000", "forbes feature"),
}


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").split())


def _contains_alias(normalized: str, alias: str) -> bool:
    pattern = rf"(?<![a-z0-9]){re.escape(_normalize_text(alias))}(?![a-z0-9])"
    return re.search(pattern, normalized) is not None


def normalize_signal_type(signal_type: str) -> str:
    normalized = _normalize_text(signal_type)
    if not normalized:
        raise IntentSignalNormalizationError("signal_type cannot be empty")
    if normalized in INTENT_RULES or normalized in CONTEXT_ONLY_SIGNAL_TYPES:
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


def normalize_signal(
    *,
    signal_type: str,
    signal_date: date,
    dedupe_key: str | None = None,
) -> NormalizedIntentSignal:
    canonical = normalize_signal_type(signal_type)

    if canonical in CONTEXT_ONLY_SIGNAL_TYPES:
        weight, half_life_days = 0.0, 1
    else:
        weight, half_life_days = INTENT_RULES[canonical]

    return NormalizedIntentSignal(
        signal_type=canonical,
        signal_date=signal_date,
        weight=weight,
        half_life_days=half_life_days,
        dedupe_key=dedupe_key,
    )


def normalize_signals(
    signals: list[tuple[str, date]],
) -> list[IntentSignalInput]:
    """Convert research labels to deterministic v3.4 scoring inputs."""
    return [
        normalize_signal(signal_type=signal_type, signal_date=signal_date).as_score_input()
        for signal_type, signal_date in signals
    ]
