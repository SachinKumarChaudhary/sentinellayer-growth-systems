from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from math import pow

BASE_QUALIFIER_POINTS = 3

FIT_AMPLIFIERS: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    ("iot_device_control", 3, ("iot", "smart lock", "app-connected", "app control", "connected device",
                               "physical safety", "front door", "home security", "surveillance camera",
                               "pet feeder", "air purifier", "water purifier", "sprinkler",
                               "breast pump", "thermostat", "telematics", "vehicle theft", "home intrusion")),
    ("drop_model", 2, ("drop-model", "sell out", "limited release", "scalper", "bot magnet",
                       "waitlist", "drop day", "collab drops", "resell at 2x", "flavor drops")),
    ("kids_minors", 2, ("coppa", "minors", "children", "kids", "teen", "youth", "toddler",
                        "baby", "infant", "pediatric", "school district", "parental consent", "kid sizing")),
    ("health_data", 2, ("hipaa", "health data", "medical record", "pregnancy", "prenatal",
                        "cycle tracking", "glucose", "diabetes", "health profile", "microbiome",
                        "fertility", "vaginal health", "intimate health")),
    ("creator_community_trust", 2, ("creator trust", "community trust", "transparency",
                                     "reddit ama", "live selling", "cult following",
                                     "mental-health optimism", "anti-scalper")),
    ("age_gated", 1, ("age-gated", "21+", "alcohol", "whiskey", "hard seltzer", "thc",
                      "cannabis", "cbd", "rolling papers")),
    ("high_ticket_financing", 1, ("financing", "installment", "affirm", "klarna", "$1000+",
                                  "high-ticket", "$500+", "stolen-card ring")),
    ("franchise_location", 1, ("franchise", "multi-location", "store network", "first franchise",
                               "showroom network")),
    ("practitioner_portal", 1, ("practitioner portal", "physician dispense", "salon channel",
                                "professional pricing", "dealer portal")),
    ("subscription", 1, ("subscription", "auto-refill", "recurring billing", "monthly delivery",
                         "membership logins")),
    ("made_in_usa", 1, ("made-in-usa", "our factory", "vertical manufacturing", "domestic manufacturing",
                        "factory floor margin")),
    ("soc2_has", 2, ("soc 2 type ii", "iso 27001", "public-company governance", "nasdaq:",
                     "nyse:", "public parent", "japanese parent governance", "german consumer giant")),
    ("soc2_needs", 2, ("enterprise procurement gate", "vendor security review",
                        "institutional governance incoming", "pe governance", "growth-fund governance",
                        "future50 scaling", "need soc 2", "procurement gate", "vendor-review window")),
)

NEGATIVE_ADJUSTMENTS: tuple[tuple[str, float, tuple[str, ...]], ...] = (
    ("corporate_route_only", -3, ("corporate route only", "parent-owned", "decisions centralized",
                                  "no local buyer", "no accessible champion", "corporate pe route")),
    ("ma_freeze", -2, ("ma freeze", "post-acquisition integration", "ownership transition",
                       "just acquired", "recently acquired", "sale exploration", "unstable ownership")),
    ("founder_departed", -1, ("stepped down", "retired", "no successor named",
                              "current ceo not surfaced", "ceo vacancy", "founder exited at sale")),
)

INTENT_RULES: dict[str, tuple[float, int]] = {
    "funding": (3, 21), "new_c_suite": (2, 45), "security_hiring": (2, 30),
    "tech_migration": (2, 45), "competitor_mention": (2, 60), "dark_funnel": (2, 14),
    "seasonal_window": (1, 9999), "franchise_launch": (2, 60), "new_market": (2, 90),
    "regulated_expansion": (2, 60), "award": (1, 90), "pricing_visit": (4, 7),
    "trial_install": (5, 14), "docs_visit": (4, 7),
}

COMPLIANCE_INTENT: dict[str, tuple[float, int]] = {
    "pci": (3, 9999), "ca_breach": (3, 9999), "ftc_click_to_cancel": (3, 9999),
    "dpdp": (2, 9999), "gdpr": (2, 9999), "soc2_requirement": (2, 9999),
}


@dataclass(frozen=True)
class IntentSignalInput:
    signal_type: str
    signal_date: date
    weight: float
    half_life_days: int


@dataclass(frozen=True)
class ScoreResult:
    fit_score: float
    fit_raw: float
    intent_score: float
    priority: str
    behavior_override: bool
    negative_flags: tuple[str, ...]
    modifiers: tuple[str, ...]
    fit_attributes: tuple[str, ...]


def _normalize_0_10(raw: float) -> float:
    if raw <= 0:
        return 0.0
    if raw >= 15:
        return 10.0
    return round(raw / 15 * 10, 2)


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def compute_fit(*, employee_count: int | None, monthly_sessions: int | None, has_login: bool, notes: str) -> tuple[float, float, tuple[str, ...], tuple[str, ...]]:
    raw = 0.0
    attrs: list[str] = []
    negatives: list[str] = []
    if employee_count is not None and 50 <= employee_count <= 500:
        raw += 1; attrs.append("employee_band")
    if monthly_sessions is not None and 100_000 <= monthly_sessions <= 5_000_000:
        raw += 1; attrs.append("traffic_band")
    if has_login:
        raw += 1; attrs.append("login_surface")
    text = notes.lower()
    for key, points, keywords in FIT_AMPLIFIERS:
        if _contains_any(text, keywords):
            raw += points; attrs.append(key)
    for key, points, keywords in NEGATIVE_ADJUSTMENTS:
        if _contains_any(text, keywords):
            raw += points; negatives.append(key)
    raw = max(0.0, raw)
    return _normalize_0_10(raw), raw, tuple(attrs), tuple(negatives)


def compute_intent(*, signals: Iterable[IntentSignalInput], today: date) -> float:
    total = 0.0
    for signal in signals:
        age = max(0, (today - signal.signal_date).days)
        freshness = pow(2.0, -age / signal.half_life_days)
        total += signal.weight * freshness
    return _normalize_0_10(total)


def route_priority(*, fit_score: float, intent_score: float, behavior_override: bool,
                   negative_flags: Iterable[str], india_bridge: bool) -> tuple[str, tuple[str, ...]]:
    flags = tuple(negative_flags)
    if behavior_override:
        return "P1", ("behavior_override",)
    if fit_score > 5 and intent_score > 5:
        priority = "P1"
    elif fit_score > 5:
        priority = "P2"
    elif intent_score > 5:
        priority = "P3"
    else:
        priority = "P4"
    priority_rank = {"P1": 1, "P2": 2, "P3": 3, "P4": 4}
    modifiers: list[str] = []
    if "corporate_route_only" in flags and priority_rank[priority] > priority_rank["P3"]:
        priority = "P3"
        modifiers.append("corporate_route_cap")
    if "ma_freeze" in flags and priority_rank[priority] > priority_rank["P2"]:
        priority = "P2"
        modifiers.append("ma_freeze_cap")
    if india_bridge and priority in ("P3", "P2"):
        priority = "P2" if priority == "P3" else "P1"
        modifiers.append("india_bridge")
    return priority, tuple(modifiers)


def score_company(*, employee_count: int | None, monthly_sessions: int | None, has_login: bool,
                  notes: str, signals: Iterable[IntentSignalInput], today: date,
                  behavior_override: bool = False, india_bridge: bool = False) -> ScoreResult:
    fit_score, fit_raw, attrs, negatives = compute_fit(
        employee_count=employee_count, monthly_sessions=monthly_sessions,
        has_login=has_login, notes=notes,
    )
    intent_score = compute_intent(signals=signals, today=today)
    priority, modifiers = route_priority(
        fit_score=fit_score, intent_score=intent_score,
        behavior_override=behavior_override, negative_flags=negatives, india_bridge=india_bridge,
    )
    return ScoreResult(
        fit_score=fit_score, fit_raw=fit_raw, intent_score=intent_score, priority=priority,
        behavior_override=behavior_override, negative_flags=negatives, modifiers=modifiers,
        fit_attributes=attrs,
    )
