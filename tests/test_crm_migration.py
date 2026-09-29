from pathlib import Path

from sentinellayer_growth_engine.crm.migration import (
    build_staged_rows,
    normalize_domain,
    normalize_email,
    normalize_linkedin,
    normalize_phone,
    parse_lead_status,
    profile_source,
    reconciliation_is_complete,
    row_hash,
)


def test_normalizers_are_deterministic():
    assert normalize_domain("https://WWW.Example.com/path") == "example.com"
    assert normalize_linkedin("linkedin.com/in/example/") == "https://www.linkedin.com/in/example"
    assert normalize_email(" User@Example.COM ") == "user@example.com"
    assert normalize_phone("+1 (212) 555-0100") == "12125550100"
    assert normalize_phone("1.234E+09") is None


def test_status_parser_preserves_raw_and_quarantines_ambiguous_demo():
    result = parse_lead_status("Product Demo Session booked on Friday 2nd Oct. Invite Sent")
    assert result.raw.startswith("Product Demo")
    assert result.category == "DEMO_BOOKED"
    assert result.actionable_due_at is None
    assert result.requires_review is True


def test_status_parser_handles_no_response():
    result = parse_lead_status("No response on both numbers")
    assert result.category == "NO_RESPONSE"
    assert result.requires_review is False


def test_profile_source_captures_schema_and_hash(tmp_path: Path):
    source = tmp_path / "leads.csv"
    source.write_text("company,buyer\nAlpha,Ada\nBeta,Bob\n", encoding="utf-8")
    snapshot = profile_source(source_name="sheet-test", path=source)
    assert snapshot.row_count == 2
    assert snapshot.headers == ["company", "buyer"]
    assert len(snapshot.file_sha256) == 64
    assert len(snapshot.sample_row_hashes) == 2


def test_staging_is_replay_stable():
    rows = [{"company": "Alpha", "lead_status": "No response"}, {"company": "Beta", "lead_status": ""}]
    first = build_staged_rows(source_name="x", snapshot_hash="abc", rows=rows)
    second = build_staged_rows(source_name="x", snapshot_hash="abc", rows=rows)
    assert [item.source_row_hash for item in first] == [item.source_row_hash for item in second]
    assert [item.disposition for item in first] == ["imported", "quarantined"]
    assert row_hash(rows[0]) == first[0].source_row_hash


def test_reconciliation_requires_no_unexplained_rows():
    assert reconciliation_is_complete(source_rows=10, imported=7, updated=1, merged=1, quarantined=1, rejected=0)
    assert not reconciliation_is_complete(source_rows=10, imported=7, updated=1, merged=1, quarantined=0, rejected=0)
