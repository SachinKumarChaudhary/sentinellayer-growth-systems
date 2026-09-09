from sentinellayer_growth_engine.enrichment_quality_gate import (
    is_valid_company_email,
    is_valid_decision_maker,
)


def test_rejects_marketing_copy_as_decision_maker() -> None:
    result = is_valid_decision_maker(
        "Athletic Brewing Company",
        "Closure Predictions",
        "Guard yourself from early indicators of risk.",
    )
    assert result.valid is False
    assert result.reason == "name_contains_search_label"


def test_rejects_company_name_as_person() -> None:
    result = is_valid_decision_maker(
        "Athletic Brewing Company",
        "Athletic Brewing Co",
        "Founder & CEO",
    )
    assert result.valid is False
    assert result.reason == "name_overlaps_company_identity"


def test_rejects_search_label_prefix() -> None:
    result = is_valid_decision_maker(
        "Cozy Earth",
        "LinkedIn. Kate Greenwood",
        "Director of Social at Cozy Earth | LinkedIn",
    )
    assert result.valid is False
    assert result.reason == "name_contains_search_label"


def test_rejects_prose_fragment_as_person() -> None:
    result = is_valid_decision_maker(
        "Ooni USA",
        "As Co",
        "Founder and Co-CEO, Darina has had an integral role in shaping the future of Ooni",
    )
    assert result.valid is False
    assert result.reason == "name_contains_search_label"


def test_rejects_prose_fragment_with_location_prefix_as_person() -> None:
    result = is_valid_decision_maker(
        "Ooni USA",
        "China. As Co",
        "Founder and Co-CEO, Darina has had an integral role in shaping the future of Ooni",
    )
    assert result.valid is False
    assert result.reason == "name_contains_search_label"


def test_accepts_real_founder_ceo() -> None:
    result = is_valid_decision_maker(
        "Athletic Brewing Company",
        "Bill Shufelt",
        "Co-Founder + CEO",
    )
    assert result.valid is True


def test_rejects_unrelated_company_email_from_third_party_page() -> None:
    assert is_valid_company_email(
        "hudabeauty.com",
        "contact@c-tech.me",
        "https://ae.linkedin.com/in/ryanaldrin",
    ) is False


def test_accepts_company_domain_email() -> None:
    assert is_valid_company_email(
        "hudabeauty.com",
        "security@hudabeauty.com",
        "https://hudabeauty.com/contact",
    ) is True


def test_rejects_third_party_email_even_on_company_page() -> None:
    assert is_valid_company_email(
        "hudabeauty.com",
        "contact@other-domain.example",
        "https://hudabeauty.com/contact",
    ) is False
