from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sentinellayer_growth_engine.phase1 import (
    HunterDiscoverAdapter,
    ScraperCityAdapter,
    process_source_record,
)
from sentinellayer_growth_engine.phase1.fingerprints import raw_fingerprint
from sentinellayer_growth_engine.phase1.models import LeadSourceRecord


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "phase1_gold.json"
ACQUIRED_AT = datetime(2026, 9, 23, 12, 0, tzinfo=UTC)


def _scraper_record(payload: dict[str, object], key: str) -> LeadSourceRecord:
    return ScraperCityAdapter().adapt(
        payload,
        acquired_at=ACQUIRED_AT,
        source_record_key=key,
    )


def test_gold_suite() -> None:
    cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["cases"]
    for case in cases:
        record = _scraper_record(case["payload"], case["key"])
        result = process_source_record(record, now=ACQUIRED_AT)
        assert result.state == case["expected_state"], case["name"]
        if "expected_domain" in case:
            assert result.canonical_lead is not None
            assert result.canonical_lead.domain == case["expected_domain"], case["name"]
        if "expected_url" in case:
            assert result.canonical_lead is not None
            assert result.canonical_lead.canonical_url == case["expected_url"], case["name"]


def test_normalization_is_replay_deterministic() -> None:
    payload = {
        "merchant_name": "  ACME   INC.  ",
        "domain": "HTTPS://WWW.Acme.com/",
        "domain_url": "https://www.acme.com/account/",
        "country_code": "us",
    }
    first = process_source_record(_scraper_record(payload, "1"), now=ACQUIRED_AT)
    second = process_source_record(_scraper_record(payload, "1"), now=ACQUIRED_AT)
    assert first.canonical_lead is not None
    assert second.canonical_lead is not None
    assert first.canonical_lead.model_dump() == second.canonical_lead.model_dump()


def test_replay_is_duplicate() -> None:
    payload = {"merchant_name": "ACME", "domain": "acme.example"}
    first_record = _scraper_record(payload, "1")
    result = process_source_record(first_record, now=ACQUIRED_AT)
    replay = process_source_record(first_record, existing_records=[first_record], now=ACQUIRED_AT)
    assert result.state == "ACCEPTED"
    assert replay.state == "DUPLICATE"
    assert replay.duplicate_decision.duplicate_type == "replay"


def test_changed_source_observation_gets_new_observation_id_and_stable_lead_id() -> None:
    first = _scraper_record({"merchant_name": "ACME", "domain": "acme.example"}, "native-1")
    changed = _scraper_record({"merchant_name": "ACME", "domain": "acme-updated.example"}, "native-1")
    assert first.source_record_id != changed.source_record_id

    first_result = process_source_record(first, now=ACQUIRED_AT)
    result = process_source_record(changed, existing_records=[first], now=ACQUIRED_AT)
    assert first_result.canonical_lead is not None
    assert result.canonical_lead is not None
    assert result.canonical_lead.lead_id == first_result.canonical_lead.lead_id
    assert result.state == "ACCEPTED"
    assert result.duplicate_decision.duplicate_type == "not_duplicate"
    assert result.duplicate_decision.rule_id == "dedupe.no_phase1_exact_match"


def test_exact_duplicate_is_explainable() -> None:
    payload = {"merchant_name": "ACME", "domain": "acme.example"}
    first = _scraper_record(payload, "1")
    second = _scraper_record(payload, "2")
    result = process_source_record(second, existing_records=[first], now=ACQUIRED_AT)
    assert result.state == "DUPLICATE"
    assert result.duplicate_decision.duplicate_type == "exact_duplicate"
    assert result.duplicate_decision.matched_source_record_ids == [first.source_record_id]
    assert result.duplicate_decision.rule_id == "dedupe.exact.source.raw_fingerprint"


def test_fuzzy_entity_merge_is_not_performed() -> None:
    first = _scraper_record({"merchant_name": "ACME INC", "domain": "acme-a.example"}, "1")
    second = _scraper_record({"merchant_name": "Acme Corporation", "domain": "acme-b.example"}, "2")
    result = process_source_record(second, existing_records=[first], now=ACQUIRED_AT)
    assert result.state != "DUPLICATE"


def test_missing_values_remain_missing() -> None:
    record = _scraper_record({"merchant_name": "ACME"}, "missing")
    result = process_source_record(record, now=ACQUIRED_AT)
    assert result.canonical_lead is not None
    assert result.canonical_lead.domain is None
    assert not any(f.code == "MISSING_IDENTITY_ANCHOR" for f in result.findings)


def test_invalid_domain_quarantines() -> None:
    record = _scraper_record({"merchant_name": "ACME", "domain": "not a domain"}, "bad-domain")
    result = process_source_record(record, now=ACQUIRED_AT)
    assert result.state == "QUARANTINED"
    assert any(f.code in {"INVALID_DOMAIN", "INVALID_NORMALIZED_DOMAIN"} for f in result.findings)


def test_hunter_adapter_is_source_agnostic_downstream() -> None:
    record = HunterDiscoverAdapter().adapt(
        {
            "organization": " ACME Corp ",
            "domain": "https://acme.example/",
            "country": "us",
            "state": "CA",
            "city": "San Francisco",
        },
        acquired_at=ACQUIRED_AT,
        source_record_key="hunter-1",
    )
    result = process_source_record(record, now=ACQUIRED_AT)
    assert result.handoff is not None
    assert result.handoff.canonical_lead.source_refs == [record.source_record_id]
    assert result.handoff.canonical_lead.domain == "acme.example"


def test_raw_fingerprint_matches_payload() -> None:
    payload = {"merchant_name": "ACME", "domain": "acme.example"}
    record = _scraper_record(payload, "fingerprint")
    assert record.raw_fingerprint == raw_fingerprint(payload)
