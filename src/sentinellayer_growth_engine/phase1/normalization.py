from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .fingerprints import (
    canonical_fingerprint_for_values,
    derive_observation_id,
    source_fingerprint,
)
from .models import (
    CanonicalLead,
    FieldObservation,
    LeadSourceRecord,
    NORMALIZATION_VERSION,
    QualityStatus,
)

_WHITESPACE = re.compile(r"\s+")
_PHONE_SEPARATORS = re.compile(r"[\s().-]+")
_CORE_TEXT_FIELDS = {"display_name", "legal_name", "region", "city", "postal_code", "platform"}


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return _WHITESPACE.sub(" ", normalized).strip()


def normalize_company_name(value: str) -> str:
    return normalize_text(value)


def normalize_domain(value: str) -> str:
    raw = normalize_text(value).lower()
    if not raw:
        return ""
    candidate = raw if "://" in raw else f"//{raw}"
    parsed = urlsplit(candidate)
    hostname = parsed.hostname or raw.split("/", 1)[0].split(":", 1)[0]
    return hostname.rstrip(".").lower()


def normalize_url(value: str) -> str:
    raw = normalize_text(value)
    if not raw:
        return ""
    candidate = raw if "://" in raw or raw.startswith("//") else raw
    parsed = urlsplit(candidate)
    if not parsed.scheme and not parsed.netloc:
        return raw.rstrip("/")
    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower() if parsed.hostname else ""
    try:
        port = parsed.port
    except ValueError:
        return raw.rstrip("/")
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    netloc = host
    if parsed.username or parsed.password:
        userinfo = parsed.username or ""
        if parsed.password is not None:
            userinfo += f":{parsed.password}"
        netloc = f"{userinfo}@{netloc}"
    if port and not default_port:
        netloc = f"{netloc}:{port}"
    path = parsed.path or ""
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def normalize_country_code(value: str) -> str:
    return normalize_text(value).upper()


def normalize_email(value: str) -> str:
    raw = normalize_text(value)
    if "@" not in raw:
        return raw
    local, domain = raw.rsplit("@", 1)
    return f"{local}@{domain.lower()}"


def normalize_phone(value: str) -> str:
    raw = normalize_text(value)
    if not raw:
        return ""
    compact = _PHONE_SEPARATORS.sub("", raw)
    if compact.startswith("+"):
        return "+" + re.sub(r"\D", "", compact[1:])
    return re.sub(r"\D", "", compact)


def _normalize_value(field: str, raw_value: Any) -> tuple[Any, str]:
    if raw_value is None:
        return None, "source supplied no value"
    if isinstance(raw_value, str):
        if not raw_value.strip():
            return None, "empty source string treated as missing"
        if field == "domain":
            return normalize_domain(raw_value), "normalized domain representation"
        if field == "canonical_url":
            return normalize_url(raw_value), "normalized URL representation"
        if field in {"email", "primary_email"}:
            return normalize_email(raw_value), "normalized email representation"
        if field in {"phone", "primary_phone"}:
            return normalize_phone(raw_value), "conservative phone representation"
        if field == "country_code":
            return normalize_country_code(raw_value), "normalized country representation"
        if field in _CORE_TEXT_FIELDS:
            return normalize_company_name(raw_value), "Unicode and whitespace normalization"
        return normalize_text(raw_value), "Unicode and whitespace normalization"
    return raw_value, "non-text source value preserved without semantic coercion"


def normalize_source_record(
    record: LeadSourceRecord,
    *,
    lead_id: str,
) -> tuple[dict[str, Any], list[FieldObservation]]:
    """Normalize source representation without inferring missing meaning."""
    values: dict[str, Any] = {}
    observations: list[FieldObservation] = []

    for binding in record.mapped_fields:
        normalized, reason = _normalize_value(binding.canonical_field, binding.raw_value)
        state = (
            "missing"
            if normalized is None
            else "normalized"
            if binding.raw_value != normalized
            else "observed"
        )
        observation = FieldObservation(
            observation_id=derive_observation_id(
                lead_id,
                binding.source_field_name,
                binding.canonical_field,
                normalized,
            ),
            lead_id=lead_id,
            source_record_id=record.source_record_id,
            field=binding.canonical_field,
            source_field_name=binding.source_field_name,
            raw_value=binding.raw_value,
            normalized_value=normalized,
            value_state=state,
            observed_at=record.acquired_at,
            adapter_version=record.adapter_version,
            normalization_version=NORMALIZATION_VERSION,
            transformation_reason=reason,
        )
        observations.append(observation)
        if normalized is not None and binding.canonical_field not in values:
            values[binding.canonical_field] = normalized

    return values, observations


def build_canonical_lead(
    record: LeadSourceRecord,
    *,
    lead_id: str,
    quality_status: QualityStatus,
    quality_finding_ids: list[str],
    now: datetime,
) -> CanonicalLead:
    values, observations = normalize_source_record(record, lead_id=lead_id)
    canonical_values = {
        "display_name": values.get("display_name"),
        "legal_name": values.get("legal_name"),
        "domain": values.get("domain"),
        "canonical_url": values.get("canonical_url"),
        "country_code": values.get("country_code"),
        "region": values.get("region"),
        "city": values.get("city"),
        "postal_code": values.get("postal_code"),
        "platform": values.get("platform"),
    }

    return CanonicalLead(
        lead_id=lead_id,
        display_name=canonical_values["display_name"],
        legal_name=canonical_values["legal_name"],
        domain=canonical_values["domain"],
        canonical_url=canonical_values["canonical_url"],
        country_code=canonical_values["country_code"],
        region=canonical_values["region"],
        city=canonical_values["city"],
        postal_code=canonical_values["postal_code"],
        platform=canonical_values["platform"],
        source_refs=[record.source_record_id],
        field_observations=observations,
        normalization_version=NORMALIZATION_VERSION,
        raw_fingerprint=record.raw_fingerprint,
        source_fingerprint=source_fingerprint(record),
        canonical_fingerprint=canonical_fingerprint_for_values(canonical_values),
        quality_status=quality_status,
        quality_finding_ids=quality_finding_ids,
        created_at=now,
        updated_at=now,
    )
