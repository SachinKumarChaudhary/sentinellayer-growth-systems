from pathlib import Path

from sentinellayer_growth_engine.crm.migration import (
    build_operational_sheet_staged_rows,
    build_staged_rows,
    normalize_domain,
    normalize_email,
    normalize_linkedin,
    normalize_phone,
    operational_sheet_profile,
    parse_operational_sheet_row,
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


def test_operational_sheet_accepts_regional_linkedin_and_space_separated_emails():
    row = {
        "company": "Example",
        "buyer": "Ada",
        "title": "CISO",
        "linkedin_url": "https://in.linkedin.com/in/ada-example",
        "Phone ": "919876543210",
        "Email": "ada@gmail.com ada@example.com",
        "Lead Status": "",
        "Intent": "",
    }
    parsed = parse_operational_sheet_row(row, source_row_number=1)
    assert parsed.linkedin_url == "https://www.linkedin.com/in/ada-example"
    assert parsed.emails == ["ada@gmail.com", "ada@example.com"]
    assert parsed.invalid_contact_values == []


def test_operational_sheet_classifies_structural_and_duplicate_rows():
    rows = [
        {"company": "", "buyer": "", "title": "", "linkedin_url": "", "Phone ": "", "Email": "", "Lead Status": "", "Intent": ""},
        {"company": "Alpha", "buyer": "Ada", "title": "CISO", "linkedin_url": "https://www.linkedin.com/in/ada", "Phone ": "", "Email": "", "Lead Status": "", "Intent": ""},
        {"company": "Beta", "buyer": "Ada", "title": "CISO", "linkedin_url": "https://www.linkedin.com/in/ada", "Phone ": "", "Email": "", "Lead Status": "", "Intent": ""},
        {"company": "Gamma", "buyer": "Bob", "title": "CTO", "linkedin_url": "Bad LinkedIn value", "Phone ": "", "Email": "", "Lead Status": "", "Intent": ""},
    ]
    staged = build_operational_sheet_staged_rows(
        source_name="sheet",
        snapshot_hash="x",
        rows=rows,
    )
    assert [x.disposition for x in staged] == ["rejected", "imported", "merged", "quarantined"]
    assert operational_sheet_profile(staged)["reconciliation_complete"] is True
