from datetime import date

import pytest

from sentinellayer_growth_engine.intent_normalization import (
    IntentSignalNormalizationError,
    normalize_signal,
    normalize_signal_type,
    normalize_signals,
)


def test_normalizes_research_labels_to_canonical_rules() -> None:
    assert normalize_signal_type("Funding round") == "funding"
    assert normalize_signal_type("security engineer hiring spike") == "security_hiring"
    assert normalize_signal_type("EU launch") == "new_market"
    assert normalize_signal_type("PCI DSS 4.0") == "pci"


def test_scoring_parameters_are_taken_from_playbook_not_input_labels() -> None:
    signal = normalize_signal(signal_type="funding round", signal_date=date(2026, 9, 1))
    assert signal.signal_type == "funding"
    assert signal.weight == 3
    assert signal.half_life_days == 21


def test_compliance_signals_use_canonical_compliance_rules() -> None:
    signal = normalize_signal(signal_type="FTC Click-to-Cancel", signal_date=date(2026, 9, 1))
    assert signal.signal_type == "ftc_click_to_cancel"
    assert signal.weight == 3
    assert signal.half_life_days == 9999


def test_unknown_signal_is_fail_closed() -> None:
    with pytest.raises(IntentSignalNormalizationError):
        normalize_signal_type("made up buying signal")


def test_ambiguous_signal_is_rejected() -> None:
    with pytest.raises(IntentSignalNormalizationError):
        normalize_signal_type("new market award")


def test_aliases_do_not_match_inside_unrelated_words() -> None:
    with pytest.raises(IntentSignalNormalizationError):
        normalize_signal_type("refunding policy")


def test_batch_normalization_preserves_dates_and_order() -> None:
    normalized = normalize_signals(
        [
            ("dark funnel complaint", date(2026, 9, 1)),
            ("new market entry", date(2026, 8, 20)),
        ]
    )
    assert [signal.signal_type for signal in normalized] == ["dark_funnel", "new_market"]
    assert [signal.signal_date for signal in normalized] == [date(2026, 9, 1), date(2026, 8, 20)]
