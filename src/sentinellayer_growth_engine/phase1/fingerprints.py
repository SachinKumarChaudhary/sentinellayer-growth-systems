from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from .models import CanonicalLead, LeadSourceRecord


def stable_json(value: Any) -> str:
    """Return deterministic JSON for hashing and equality checks."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def fingerprint(value: Any) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def raw_fingerprint(source_payload: Mapping[str, Any]) -> str:
    return fingerprint(dict(source_payload))


def source_fingerprint(record: LeadSourceRecord) -> str:
    projection = {
        "source_name": record.source_name,
        "source_version": record.source_version,
        "source_record_key": record.source_record_key,
        "adapter_version": record.adapter_version,
        "mapped_fields": [
            {
                "canonical_field": item.canonical_field,
                "source_field_name": item.source_field_name,
                "raw_value": item.raw_value,
            }
            for item in record.mapped_fields
        ],
    }
    return fingerprint(projection)


def canonical_projection(lead: CanonicalLead) -> dict[str, Any]:
    return {
        "display_name": lead.display_name,
        "legal_name": lead.legal_name,
        "domain": lead.domain,
        "canonical_url": lead.canonical_url,
        "country_code": lead.country_code,
        "region": lead.region,
        "city": lead.city,
        "postal_code": lead.postal_code,
        "platform": lead.platform,
    }


def canonical_fingerprint_for_values(values: Mapping[str, Any]) -> str:
    return fingerprint(
        {
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
    )


def derive_source_record_id(
    source_name: str,
    source_record_key: str | None,
    raw_fp: str,
) -> str:
    identity_material = {
        "source_name": source_name.strip().lower(),
        "source_record_key": source_record_key,
        "raw_fingerprint": raw_fp,
    }
    return f"sr_{fingerprint(identity_material)[:40]}"


def derive_lead_id(source_record_id: str) -> str:
    return f"lead_{fingerprint(source_record_id)[:40]}"


def derive_observation_id(
    lead_id: str,
    source_field_name: str,
    canonical_field: str,
    normalized_value: Any,
) -> str:
    material = {
        "lead_id": lead_id,
        "source_field_name": source_field_name,
        "canonical_field": canonical_field,
        "normalized_value": normalized_value,
    }
    return f"obs_{fingerprint(material)[:40]}"


def derive_finding_id(
    *,
    source_record_id: str | None,
    lead_id: str | None,
    rule_id: str,
    field: str | None,
    code: str,
    observed_value_ref: str | None,
    validation_version: str,
) -> str:
    material = {
        "source_record_id": source_record_id,
        "lead_id": lead_id,
        "rule_id": rule_id,
        "field": field,
        "code": code,
        "observed_value_ref": observed_value_ref,
        "validation_version": validation_version,
    }
    return f"finding_{fingerprint(material)[:40]}"


def derive_duplicate_decision_id(source_record_id: str, rule_id: str) -> str:
    material = {
        "source_record_id": source_record_id,
        "rule_id": rule_id,
    }
    return f"dup_{fingerprint(material)[:40]}"
