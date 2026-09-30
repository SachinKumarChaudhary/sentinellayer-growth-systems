import pytest

from sentinellayer_growth_engine.crm.state import StateTransitionError, validate_state_transition


def test_account_positive_path():
    validate_state_transition(entity_type="account", current_state="NEW", target_state="QUALIFIED")
    validate_state_transition(entity_type="account", current_state="QUALIFIED", target_state="WORKING")
    validate_state_transition(entity_type="account", current_state="WORKING", target_state="ENGAGED")
    validate_state_transition(entity_type="account", current_state="ENGAGED", target_state="SALES_QUALIFIED")
    validate_state_transition(entity_type="account", current_state="SALES_QUALIFIED", target_state="CUSTOMER")


def test_contact_reply_path():
    validate_state_transition(entity_type="contact", current_state="NOT_CONTACTED", target_state="CONTACTED")
    validate_state_transition(entity_type="contact", current_state="CONTACTED", target_state="REPLIED")
    validate_state_transition(entity_type="contact", current_state="REPLIED", target_state="FOLLOW_UP")


def test_invalid_transition_rejected():
    with pytest.raises(StateTransitionError):
        validate_state_transition(entity_type="account", current_state="NEW", target_state="CUSTOMER")


def test_same_state_rejected():
    with pytest.raises(StateTransitionError):
        validate_state_transition(entity_type="contact", current_state="REPLIED", target_state="REPLIED")


def test_unsuppress_requires_explicit_authorization():
    with pytest.raises(StateTransitionError):
        validate_state_transition(entity_type="account", current_state="SUPPRESSED", target_state="NURTURE")
    validate_state_transition(
        entity_type="account", current_state="SUPPRESSED", target_state="NURTURE", explicit_unsuppress=True
    )
