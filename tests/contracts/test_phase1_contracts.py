from __future__ import annotations

from datetime import datetime, timezone

from sentinellayer_growth_engine.contracts import validate_contract
from sentinellayer_growth_engine.phase1 import ScraperCityAdapter, process_source_record


def test_phase1_contracts_accept_realistic_handoff() -> None:
    now = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)
    record = ScraperCityAdapter().adapt(
        {
            "merchant_name": "ACME Inc.",
            "domain": "HTTPS://WWW.acme.example/",
            "domain_url": "https://www.acme.example/",
            "country_code": "US",
        },
        acquired_at=now,
        source_record_key="row-1",
    )
    result = process_source_record(record, now=now)
    assert result.handoff is not None

    validate_contract("lead_source_record", record.model_dump(mode="json"))
    validate_contract("canonical_lead", result.canonical_lead.model_dump(mode="json"))
    validate_contract("phase1_handoff", result.handoff.model_dump(mode="json"))
    for observation in result.handoff.field_observations:
        validate_contract("field_observation", observation.model_dump(mode="json"))
    for finding in result.handoff.quality_findings:
        validate_contract("validation_finding", finding.model_dump(mode="json"))


def test_phase1_contracts_reject_extra_fields() -> None:
    now = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)
    record = ScraperCityAdapter().adapt(
        {"merchant_name": "ACME", "domain": "acme.example"},
        acquired_at=now,
        source_record_key="row-2",
    )
    payload = record.model_dump(mode="json")
    payload["unexpected"] = "must fail"
    try:
        validate_contract("lead_source_record", payload)
    except ValueError as exc:
        assert "contract validation failed" in str(exc)
    else:
        raise AssertionError("extra contract fields must be rejected")
