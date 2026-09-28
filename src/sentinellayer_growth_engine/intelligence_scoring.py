from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from math import pow


SCORING_VERSION = "v3.4-exec1"

# ---------------------------------------------------------------------------
# FIT
# ---------------------------------------------------------------------------
# FIT is the upstream ICP/structural-suitability dimension. This module keeps
# the existing deterministic FIT calculation, but FIT is not itself intent.
FIT_AMPLIFIERS: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    ("iot_device_control", 3, ("iot", "smart lock", "app-connected", "app control", "connected device", "physical safety", "front door", "home security", "surveillance camera", "pet feeder", "air purifier", "water purifier", "sprinkler", "breast pump", "thermostat", "telematics", "vehicle theft", "home intrusion")),
    ("drop_model", 2, ("drop-model", "sell out", "limited release", "scalper", "bot magnet", "waitlist", "drop day", "collab drops", "resell at 2x", "flavor drops")),
    ("kids_minors", 2, ("coppa", "minors", "children", "kids", "teen", "youth", "toddler", "baby", "infant", "pediatric", "school district", "parental consent", "kid sizing")),
    ("health_data", 2, ("hipaa", "health data", "medical record", "pregnancy", "prenatal", "cycle tracking", "glucose", "diabetes", "health profile", "microbiome", "fertility", "vaginal health", "intimate health")),
    ("creator_community_trust", 2, ("creator trust", "community trust", "transparency", "reddit ama", "live selling", "cult following", "mental-health optimism", "anti-scalper")),
    ("age_gated", 1, ("age-gated", "21+", "alcohol", "whiskey", "hard seltzer", "thc", "cannabis", "cbd", "rolling papers")),
    ("high_ticket_financing", 1, ("financing", "installment", "affirm", "klarna", "$1000+", "high-ticket", "$500+", "stolen-card ring")),
    ("franchise_location", 1, ("franchise", "multi-location", "store network", "first franchise", "showroom network")),
    ("practitioner_portal", 1, ("practitioner portal", "physician dispense", "salon channel", "professional pricing", "dealer portal")),
    ("subscription", 1, ("subscription", "auto-refill", "recurring billing", "monthly delivery", "membership logins")),
    ("made_in_usa", 1, ("made-in-usa", "our factory", "vertical manufacturing", "domestic manufacturing", "factory floor margin")),
    ("soc2_has", 2, ("soc 2 type ii", "iso 27001", "public-company governance", "nasdaq:", "nyse:", "public parent", "japanese parent governance", "german consumer giant")),
    ("soc2_needs", 2, ("enterprise procurement gate", "vendor security review", "institutional governance incoming", "pe governance", "growth-fund governance", "future50 scaling", "need soc 2", "procurement gate", "vendor-review window")),
)

NEGATIVE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("corporate_route_only", ("corporate route only", "parent-owned", "decisions centralized", "no local buyer", "no accessible champion", "corporate pe route")),
    ("ma_freeze", ("ma freeze", "post-acquisition integration", "ownership transition", "just acquired", "recently acquired", "sale exploration", "unstable ownership")),
    ("founder_departed", ("stepped down", "retired", "no successor named", "current ceo not surfaced", "ceo vacancy", "founder exited at sale")),
    ("business_contraction", ("major layoffs", "mass layoffs", "store closures", "sustained user decline", "revenue contraction", "downsizing", "restructuring")),
)

# v3.4 recommended intent weights / half-lives.
INTENT_RULES: dict[str, tuple[float, int]] = {
    "trial_install": (5, 14),
    "sdk_install": (5, 14),
    "evaluate_activity": (5, 14),
    "pricing_visit": (4, 7),
    "docs_visit": (4, 7),
    "explicit_incident": (4, 14),
    "competitor_evaluation": (3, 30),
    "security_hiring": (3, 30),
    "new_security_leader": (3, 45),
    "tech_migration": (3, 45),
    "authenticated_product_change": (2, 45),
    "funding": (3, 21),
    "new_market": (2, 60),
    "executive_business_event": (2, 45),
    "franchise_launch": (2, 60),
    "seasonal_window": (1, 9999),
    "regulated_expansion": (2, 60),
}

# v3.4 explicitly separates context from intent. These labels remain valid
# research outputs but do not contribute to the main intent score by themselves.
CONTEXT_ONLY_SIGNAL_TYPES = {
    "dark_funnel",
    "pci",
    "ca_breach",
    "ftc_click_to_cancel",
    "dpdp",
    "gdpr",
    "soc2_requirement",
    "award",
}

BEHAVIOR_P1_STAGES = {
    "IDENTIFIED_TECHNICAL_EVALUATION",
    "COMMERCIAL_EVALUATION",
    "ACTIVE_EVALUATION",
    "DEPLOYMENT",
    "PRODUCT_QUALIFIED",
}


@dataclass(frozen=True)
class IntentSignalInput:
    signal_type: str
    signal_date: date
    weight: float
    half_life_days: int
    dedupe_key: str | None = None


@dataclass(frozen=True)
class IntentContribution:
    signal_type: str
    signal_date: date
    age_days: int
    freshness: float
    value: float
    dedupe_key: str


@dataclass(frozen=True)
class ScoreResult:
    fit_score: float
    fit_raw: float
    intent_score: float
    raw_intent: float
    intent_components: tuple[IntentContribution, ...]
    priority: str
    behavior_override: bool
    behavior_stage: str | None
    negative_flags: tuple[str, ...]
    modifiers: tuple[str, ...]
    fit_attributes: tuple[str, ...]


def _normalize_0_10(raw: float) -> float:
    """v3.4 executable interpretation: additive score capped at 10."""
    return round(min(10.0, max(0.0, raw)), 2)


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _detect_negative_flags(text: str) -> tuple[str, ...]:
    return tuple(key for key, keywords in NEGATIVE_RULES if _contains_any(text, keywords))


def compute_fit(
    *,
    employee_count: int | None,
    monthly_sessions: int | None,
    has_login: bool,
    notes: str,
) -> tuple[float, float, tuple[str, ...], tuple[str, ...]]:
    """Deterministic structural FIT calculation.

    Negative/friction flags are detected for routing context, but they are not
    subtracted from FIT. v3.4 applies them after FIT/INTENT calculation.
    """
    raw = 0.0
    attrs: list[str] = []

    if employee_count is not None and 50 <= employee_count <= 500:
        raw += 1
        attrs.append("employee_band")
    if monthly_sessions is not None and 100_000 <= monthly_sessions <= 5_000_000:
        raw += 1
        attrs.append("traffic_band")
    if has_login:
        raw += 1
        attrs.append("login_surface")

    text = notes.lower()
    for key, points, keywords in FIT_AMPLIFIERS:
        if _contains_any(text, keywords):
            raw += points
            attrs.append(key)

    return _normalize_0_10(raw), raw, tuple(attrs), _detect_negative_flags(text)


def compute_intent(
    *,
    signals: Iterable[IntentSignalInput],
    today: date,
) -> tuple[float, float, tuple[IntentContribution, ...]]:
    """Return intent score, raw intent, and an auditable contribution ledger.

    Duplicate copies of one event count once. When no explicit event key is
    supplied, (signal_type, signal_date) is used as a conservative identity.
    """
    total = 0.0
    seen: set[str] = set()
    contributions: list[IntentContribution] = []

    for signal in signals:
        canonical = signal.signal_type.strip().lower()
        if canonical in CONTEXT_ONLY_SIGNAL_TYPES or signal.weight <= 0:
            continue

        key = signal.dedupe_key or f"{canonical}:{signal.signal_date.isoformat()}"
        if key in seen:
            continue
        seen.add(key)

        age = max(0, (today - signal.signal_date).days)
        half_life = max(1, signal.half_life_days)
        freshness = pow(2.0, -age / half_life)
        value = signal.weight * freshness
        total += value
        contributions.append(
            IntentContribution(
                signal_type=canonical,
                signal_date=signal.signal_date,
                age_days=age,
                freshness=round(freshness, 4),
                value=round(value, 4),
                dedupe_key=key,
            )
        )

    contributions.sort(key=lambda item: (-item.value, item.signal_date, item.signal_type))
    return _normalize_0_10(total), total, tuple(contributions)


def route_priority(
    *,
    fit_score: float,
    intent_score: float,
    behavior_override: bool,
    behavior_stage: str | None,
    negative_flags: Iterable[str],
    india_bridge: bool,
    decision_maker_depth: int = 0,
) -> tuple[str, tuple[str, ...]]:
    flags = tuple(sorted(set(negative_flags)))
    modifiers: list[str] = []

    behavior_p1 = behavior_override or behavior_stage in BEHAVIOR_P1_STAGES
    if behavior_p1:
        priority = "P1"
        modifiers.append("behavior_p1")
    elif fit_score > 5 and intent_score > 5:
        priority = "P1"
    elif fit_score > 5:
        priority = "P2"
    elif intent_score > 5:
        priority = "P3"
    else:
        priority = "P4"

    # Relationship modifier. It does not override organizational routing caps.
    if india_bridge and priority in ("P3", "P2"):
        priority = "P2" if priority == "P3" else "P1"
        modifiers.append("india_bridge")

    # v3.4 negative/friction policies are applied after positive routing
    # modifiers, preserving the parent-company and M&A caps.
    if "corporate_route_only" in flags:
        if priority in ("P1", "P2"):
            priority = "P3"
        modifiers.append("corporate_route_cap")

    if "ma_freeze" in flags:
        if priority == "P1":
            priority = "P2"
        modifiers.append("ma_freeze_cap")

    if "business_contraction" in flags:
        modifiers.append("business_contraction_friction")
    if "founder_departed" in flags:
        modifiers.append("founder_transition_friction")
    if decision_maker_depth >= 2:
        modifiers.append("decision_maker_depth")

    return priority, tuple(modifiers)


def score_company(
    *,
    employee_count: int | None,
    monthly_sessions: int | None,
    has_login: bool,
    notes: str,
    signals: Iterable[IntentSignalInput],
    today: date,
    behavior_override: bool = False,
    behavior_stage: str | None = None,
    india_bridge: bool = False,
    decision_maker_depth: int = 0,
) -> ScoreResult:
    fit_score, fit_raw, attrs, negatives = compute_fit(
        employee_count=employee_count,
        monthly_sessions=monthly_sessions,
        has_login=has_login,
        notes=notes,
    )
    intent_score, raw_intent, components = compute_intent(signals=signals, today=today)
    priority, modifiers = route_priority(
        fit_score=fit_score,
        intent_score=intent_score,
        behavior_override=behavior_override,
        behavior_stage=behavior_stage,
        negative_flags=negatives,
        india_bridge=india_bridge,
        decision_maker_depth=decision_maker_depth,
    )
    return ScoreResult(
        fit_score=fit_score,
        fit_raw=fit_raw,
        intent_score=intent_score,
        raw_intent=round(raw_intent, 4),
        intent_components=components,
        priority=priority,
        behavior_override=behavior_override or behavior_stage in BEHAVIOR_P1_STAGES,
        behavior_stage=behavior_stage,
        negative_flags=negatives,
        modifiers=modifiers,
        fit_attributes=attrs,
    )
