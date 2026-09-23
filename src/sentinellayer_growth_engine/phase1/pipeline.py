from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from .fingerprints import derive_duplicate_decision_id, derive_lead_id
from .models import (
    DuplicateDecision,
    DuplicateType,
    LeadSourceRecord,
    Phase1Handoff,
    Phase1Result,
    RecordState,
)
from .normalization import build_canonical_lead
from .validation import has_errors, has_warnings, validate_canonical_lead, validate_source_record


def _now() -> datetime:
    return datetime.now(UTC)


def _duplicate_decision(
    *,
    source_record_id: str,
    duplicate_type: DuplicateType,
    rule_id: str,
    matched_ids: list[str],
    comparison_keys: dict[str, object],
    decided_at: datetime,
) -> DuplicateDecision:
    return DuplicateDecision(
        decision_id=derive_duplicate_decision_id(source_record_id, rule_id),
        source_record_id=source_record_id,
        duplicate_type=duplicate_type,
        rule_id=rule_id,
        matched_source_record_ids=matched_ids,
        comparison_keys=comparison_keys,
        decided_at=decided_at,
        decision_version="phase1.dedupe.v1",
    )


def _check_duplicate(
    source_record_id: str,
    source_name: str,
    source_record_key: str | None,
    raw_fingerprint: str,
    existing_records: Sequence[LeadSourceRecord],
    decided_at: datetime,
) -> DuplicateDecision:
    for existing in existing_records:
        if existing.source_record_id == source_record_id:
            return _duplicate_decision(
                source_record_id=source_record_id,
                duplicate_type="replay",
                rule_id="dedupe.replay.source_record_id",
                matched_ids=[existing.source_record_id],
                comparison_keys={"source_record_id": source_record_id},
                decided_at=decided_at,
            )

    for existing in existing_records:
        if (
            existing.source_name == source_name
            and existing.raw_fingerprint == raw_fingerprint
            and existing.source_record_id != source_record_id
        ):
            return _duplicate_decision(
                source_record_id=source_record_id,
                duplicate_type="exact_duplicate",
                rule_id="dedupe.exact.source.raw_fingerprint",
                matched_ids=[existing.source_record_id],
                comparison_keys={
                    "source_name": source_name,
                    "raw_fingerprint": raw_fingerprint,
                },
                decided_at=decided_at,
            )

    return _duplicate_decision(
        source_record_id=source_record_id,
        duplicate_type="not_duplicate",
        rule_id="dedupe.no_phase1_exact_match",
        matched_ids=[],
        comparison_keys={
            "source_name": source_name,
            "source_record_key": source_record_key,
            "raw_fingerprint": raw_fingerprint,
        },
        decided_at=decided_at,
    )


def process_source_record(
    record: LeadSourceRecord,
    *,
    existing_records: Sequence[LeadSourceRecord] = (),
    now: datetime | None = None,
) -> Phase1Result:
    processed_at = now or _now()
    source_findings = validate_source_record(record, now=processed_at)
    lead_id = derive_lead_id(record.source_record_id)

    provisional_status = "QUARANTINED" if has_errors(source_findings) else "ACCEPTED"
    lead = build_canonical_lead(
        record,
        lead_id=lead_id,
        quality_status=provisional_status,
        quality_finding_ids=[item.finding_id for item in source_findings],
        now=processed_at,
    )
    canonical_findings = validate_canonical_lead(lead, now=processed_at)
    findings = [*source_findings, *canonical_findings]

    if has_errors(findings):
        quality_status = "QUARANTINED"
        state: RecordState = "QUARANTINED"
    elif has_warnings(findings):
        quality_status = "ACCEPTED_WITH_WARNINGS"
        state = "ACCEPTED_WITH_WARNINGS"
    else:
        quality_status = "ACCEPTED"
        state = "ACCEPTED"

    lead = lead.model_copy(
        update={
            "quality_status": quality_status,
            "quality_finding_ids": [item.finding_id for item in findings],
            "updated_at": processed_at,
        }
    )

    duplicate = _check_duplicate(
        source_record_id=record.source_record_id,
        source_name=record.source_name,
        source_record_key=record.source_record_key,
        raw_fingerprint=record.raw_fingerprint,
        existing_records=existing_records,
        decided_at=processed_at,
    )

    if duplicate.duplicate_type in {"replay", "exact_duplicate"}:
        state = "DUPLICATE"
        lead = lead.model_copy(update={"quality_status": "DUPLICATE"})

    handoff = None
    if state in {"ACCEPTED", "ACCEPTED_WITH_WARNINGS"}:
        handoff = Phase1Handoff(
            lead_id=lead.lead_id,
            canonical_lead=lead,
            source_refs=lead.source_refs,
            field_observations=lead.field_observations,
            quality_status=lead.quality_status,
            quality_findings=findings,
            normalization_version=lead.normalization_version,
            canonical_fingerprint=lead.canonical_fingerprint,
            contract_version="phase1.handoff.v1",
            downstream_eligible=True,
            completed_at=processed_at,
        )

    return Phase1Result(
        state=state,
        source_record=record,
        canonical_lead=lead,
        findings=findings,
        duplicate_decision=duplicate,
        handoff=handoff,
    )
