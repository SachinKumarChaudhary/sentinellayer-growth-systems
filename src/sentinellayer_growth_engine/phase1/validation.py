from __future__ import annotations

import re
from datetime import UTC, datetime

from .fingerprints import derive_finding_id, raw_fingerprint
from .models import (
    CanonicalLead,
    FindingSeverity,
    LeadSourceRecord,
    ValidationFinding,
)

VALIDATION_VERSION = "phase1.validation.v1"
_COUNTRY_RE = re.compile(r"^[A-Z]{2}$")
_DOMAIN_RE = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{0,253}[a-z0-9])?$", re.IGNORECASE)


def _now(now: datetime | None) -> datetime:
    return now or datetime.now(UTC)


def _finding(
    *,
    source_record_id: str | None,
    lead_id: str | None,
    field: str | None,
    rule_id: str,
    severity: FindingSeverity,
    code: str,
    message: str,
    observed_value_ref: str | None,
    now: datetime,
) -> ValidationFinding:
    return ValidationFinding(
        finding_id=derive_finding_id(
            source_record_id=source_record_id,
            lead_id=lead_id,
            rule_id=rule_id,
            field=field,
            code=code,
            observed_value_ref=observed_value_ref,
            validation_version=VALIDATION_VERSION,
        ),
        source_record_id=source_record_id,
        lead_id=lead_id,
        field=field,
        rule_id=rule_id,
        severity=severity,
        code=code,
        message=message,
        observed_value_ref=observed_value_ref,
        created_at=now,
        validation_version=VALIDATION_VERSION,
    )


def validate_source_record(
    record: LeadSourceRecord,
    *,
    now: datetime | None = None,
) -> list[ValidationFinding]:
    checked_at = _now(now)
    findings: list[ValidationFinding] = []

    if not record.source_payload:
        findings.append(
            _finding(
                source_record_id=record.source_record_id,
                lead_id=None,
                field=None,
                rule_id="source_payload.non_empty",
                severity="ERROR",
                code="EMPTY_SOURCE_PAYLOAD",
                message="source_payload must contain the immutable raw source observation",
                observed_value_ref=None,
                now=checked_at,
            )
        )

    expected_raw = raw_fingerprint(record.source_payload)
    if expected_raw != record.raw_fingerprint:
        findings.append(
            _finding(
                source_record_id=record.source_record_id,
                lead_id=None,
                field=None,
                rule_id="fingerprint.raw_matches_payload",
                severity="ERROR",
                code="RAW_FINGERPRINT_MISMATCH",
                message="raw_fingerprint does not match the stored source_payload",
                observed_value_ref=record.raw_fingerprint,
                now=checked_at,
            )
        )

    for binding in record.mapped_fields:
        if binding.canonical_field == "domain" and binding.raw_value:
            domain = str(binding.raw_value).strip().lower()
            if "://" in domain:
                domain = domain.split("://", 1)[1]
            domain = domain.split("/", 1)[0].split(":", 1)[0].rstrip(".")
            if not domain or not _DOMAIN_RE.fullmatch(domain) or "." not in domain:
                findings.append(
                    _finding(
                        source_record_id=record.source_record_id,
                        lead_id=None,
                        field="domain",
                        rule_id="field.domain.syntax",
                        severity="ERROR",
                        code="INVALID_DOMAIN",
                        message="domain is not a syntactically plausible web domain",
                        observed_value_ref="domain",
                        now=checked_at,
                    )
                )

        if binding.canonical_field == "country_code" and binding.raw_value:
            country = str(binding.raw_value).strip().upper()
            if not _COUNTRY_RE.fullmatch(country):
                findings.append(
                    _finding(
                        source_record_id=record.source_record_id,
                        lead_id=None,
                        field="country_code",
                        rule_id="field.country_code.format",
                        severity="WARNING",
                        code="INVALID_COUNTRY_CODE_FORMAT",
                        message="country_code is not a two-letter uppercase country representation",
                        observed_value_ref="country_code",
                        now=checked_at,
                    )
                )

    return findings


def validate_canonical_lead(
    lead: CanonicalLead,
    *,
    now: datetime | None = None,
) -> list[ValidationFinding]:
    checked_at = _now(now)
    findings: list[ValidationFinding] = []

    if not any((lead.display_name, lead.domain, lead.canonical_url)):
        findings.append(
            _finding(
                source_record_id=lead.source_refs[0],
                lead_id=lead.lead_id,
                field=None,
                rule_id="semantic.identity_anchor",
                severity="ERROR",
                code="MISSING_IDENTITY_ANCHOR",
                message="at least one explicit identity anchor (display_name, domain, canonical_url) is required",
                observed_value_ref=None,
                now=checked_at,
            )
        )

    if lead.domain and (not _DOMAIN_RE.fullmatch(lead.domain) or "." not in lead.domain):
        findings.append(
            _finding(
                source_record_id=lead.source_refs[0],
                lead_id=lead.lead_id,
                field="domain",
                rule_id="field.domain.normalized_syntax",
                severity="ERROR",
                code="INVALID_NORMALIZED_DOMAIN",
                message="normalized domain is not a syntactically plausible web domain",
                observed_value_ref=lead.domain,
                now=checked_at,
            )
        )

    if lead.country_code and not _COUNTRY_RE.fullmatch(lead.country_code):
        findings.append(
            _finding(
                source_record_id=lead.source_refs[0],
                lead_id=lead.lead_id,
                field="country_code",
                rule_id="field.country_code.normalized_format",
                severity="WARNING",
                code="INVALID_NORMALIZED_COUNTRY_CODE",
                message="normalized country code is not two uppercase letters",
                observed_value_ref=lead.country_code,
                now=checked_at,
            )
        )

    by_field: dict[str, set[str]] = {}
    for observation in lead.field_observations:
        if observation.normalized_value is None:
            continue
        by_field.setdefault(observation.field, set()).add(str(observation.normalized_value))

    for field, values in sorted(by_field.items()):
        if len(values) > 1:
            findings.append(
                _finding(
                    source_record_id=lead.source_refs[0],
                    lead_id=lead.lead_id,
                    field=field,
                    rule_id="cross_field.single_canonical_value",
                    severity="WARNING",
                    code="CONFLICTING_VALUES",
                    message="multiple source observations map to the same canonical field with different normalized values",
                    observed_value_ref=field,
                    now=checked_at,
                )
            )

    return findings


def has_errors(findings: list[ValidationFinding]) -> bool:
    return any(item.severity == "ERROR" for item in findings)


def has_warnings(findings: list[ValidationFinding]) -> bool:
    return any(item.severity == "WARNING" for item in findings)
