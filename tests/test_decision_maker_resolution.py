from sentinellayer_growth_engine.decision_maker_resolution import (
    DecisionMakerCandidate,
    merge_candidate_sources,
    normalize_linkedin_url,
    outreach_status,
    rank_candidates,
    score_identity,
)


def test_normalize_linkedin_profile_url_drops_tracking_query():
    assert normalize_linkedin_url(
        "https://www.linkedin.com/in/jane-doe/?trk=foo&utm_source=bar"
    ) == "https://www.linkedin.com/in/jane-doe"


def test_normalize_linkedin_rejects_non_profile_urls():
    assert normalize_linkedin_url("https://www.linkedin.com/company/acme") is None
    assert normalize_linkedin_url("https://example.com/in/jane") is None


def test_identity_score_requires_evidence_not_just_name():
    score, reasons = score_identity(
        name_matches=True,
        current_company_matches=False,
        title_matches=True,
        company_site_supports_person=False,
        independent_source_supports_person=False,
    )
    assert score == 0.5
    assert "current_company_match" not in reasons


def test_identity_score_penalizes_former_and_stale_employment():
    score, reasons = score_identity(
        name_matches=True,
        current_company_matches=True,
        title_matches=True,
        company_site_supports_person=True,
        independent_source_supports_person=True,
        former_employee=True,
        stale_employment=True,
    )
    assert score == 0.75
    assert "former_employee_penalty" in reasons
    assert "stale_employment_penalty" in reasons


def test_outreach_status_blocks_missing_linkedin_and_low_employer_confidence():
    assert outreach_status(0.99, linkedin_url=None, current_company_confidence=0.99) == "review"
    assert outreach_status(0.99, linkedin_url="https://www.linkedin.com/in/jane", current_company_confidence=0.74) == "review"
    assert outreach_status(0.90, linkedin_url="https://www.linkedin.com/in/jane", current_company_confidence=0.75) == "outreach_ready"


def test_merge_sources_preserves_provenance_and_best_linkedin():
    a = DecisionMakerCandidate(
        full_name="Jane Doe",
        title="CTO",
        company_name="Acme",
        source_urls=("https://acme.com/team",),
        source_types=("company_site",),
        current_employer_confidence=0.9,
        title_confidence=0.8,
        overall_confidence=0.8,
    )
    b = DecisionMakerCandidate(
        full_name="Jane Doe",
        title="Chief Technology Officer",
        company_name="Acme",
        linkedin_url="https://linkedin.com/in/jane-doe/?trk=abc",
        source_urls=("https://www.linkedin.com/in/jane-doe/?trk=abc",),
        source_types=("public_search",),
        current_employer_confidence=0.95,
        title_confidence=0.95,
        linkedin_confidence=0.85,
        overall_confidence=0.92,
    )
    merged = merge_candidate_sources(a, b)
    assert merged.linkedin_url == "https://www.linkedin.com/in/jane-doe"
    assert merged.current_employer_confidence == 0.95
    assert merged.source_types == ("company_site", "public_search")


def test_rank_candidates_puts_ready_first_then_confidence():
    review = DecisionMakerCandidate(full_name="A", overall_confidence=0.99, status="review")
    ready = DecisionMakerCandidate(full_name="B", overall_confidence=0.90, status="outreach_ready", linkedin_confidence=0.8)
    assert [c.full_name for c in rank_candidates([review, ready])] == ["B", "A"]
