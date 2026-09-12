import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinellayer_growth_engine.decision_maker_resolution import (
    DecisionMakerCandidate,
    merge_candidate_sources,
    normalize_linkedin_url,
    outreach_status,
    rank_candidates,
    score_identity,
)


def test_normalize_linkedin_profile_url():
    assert normalize_linkedin_url("https://www.linkedin.com/in/jane-doe/?trk=foo") == "https://www.linkedin.com/in/jane-doe"


def test_normalize_rejects_non_profile_urls():
    assert normalize_linkedin_url("https://www.linkedin.com/company/acme") is None
    assert normalize_linkedin_url("https://example.com/in/jane") is None


def test_identity_score_does_not_equate_name_with_company_identity():
    score, reasons = score_identity(
        name_matches=True,
        current_company_matches=False,
        title_matches=True,
        company_site_supports_person=False,
        independent_source_supports_person=False,
    )
    assert score == 0.5
    assert "current_company_match" not in reasons


def test_former_employment_is_penalized():
    score, reasons = score_identity(
        name_matches=True,
        current_company_matches=True,
        title_matches=True,
        company_site_supports_person=True,
        independent_source_supports_person=True,
        former_employee=True,
    )
    assert score == 0.75
    assert "former_employee_penalty" in reasons


def test_outreach_ready_requires_linkedin_and_current_employer_confidence():
    assert outreach_status(0.99, linkedin_url=None, current_company_confidence=0.99) == "review"
    assert outreach_status(0.99, linkedin_url="https://www.linkedin.com/in/jane-doe", current_company_confidence=0.74) == "review"
    assert outreach_status(0.90, linkedin_url="https://www.linkedin.com/in/jane-doe", current_company_confidence=0.75) == "outreach_ready"


def test_source_merge_preserves_provenance():
    merged = merge_candidate_sources(
        DecisionMakerCandidate(full_name="Jane Doe", source_urls=("https://acme.com/team",), source_types=("company_site",), overall_confidence=0.8),
        DecisionMakerCandidate(full_name="Jane Doe", linkedin_url="https://linkedin.com/in/jane-doe/?trk=x", source_urls=("https://linkedin.com/in/jane-doe",), source_types=("public_search",), current_employer_confidence=0.95, overall_confidence=0.92),
    )
    assert merged.linkedin_url == "https://www.linkedin.com/in/jane-doe"
    assert merged.source_types == ("company_site", "public_search")
    assert merged.current_employer_confidence == 0.95


def test_ready_candidate_ranks_before_higher_confidence_review_candidate():
    candidates = [
        DecisionMakerCandidate(full_name="Review", overall_confidence=0.99, status="review"),
        DecisionMakerCandidate(full_name="Ready", overall_confidence=0.90, status="outreach_ready"),
    ]
    assert [c.full_name for c in rank_candidates(candidates)] == ["Ready", "Review"]
