from __future__ import annotations

from typing import Final, Literal

EntityType = Literal["account", "contact"]

ACCOUNT_STATES: Final[frozenset[str]] = frozenset({
    "NEW", "QUALIFIED", "WORKING", "ENGAGED", "FOLLOW_UP",
    "SALES_QUALIFIED", "CUSTOMER", "NOT_INTERESTED", "NURTURE", "SUPPRESSED",
})

CONTACT_STATES: Final[frozenset[str]] = frozenset({
    "NOT_CONTACTED", "CONTACTED", "CONNECTED", "REPLIED", "FOLLOW_UP", "SUPPRESSED",
})
ACCOUNT_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
    "NEW": frozenset({"QUALIFIED", "SUPPRESSED"}),
    "QUALIFIED": frozenset({"WORKING", "NURTURE", "SUPPRESSED"}),
    "WORKING": frozenset({"ENGAGED", "FOLLOW_UP", "NOT_INTERESTED", "NURTURE", "SUPPRESSED"}),
    "ENGAGED": frozenset({"FOLLOW_UP", "SALES_QUALIFIED", "NOT_INTERESTED", "NURTURE", "SUPPRESSED"}),
    "FOLLOW_UP": frozenset({"ENGAGED", "SALES_QUALIFIED", "NOT_INTERESTED", "NURTURE", "SUPPRESSED"}),
    "SALES_QUALIFIED": frozenset({"CUSTOMER", "FOLLOW_UP", "NOT_INTERESTED", "NURTURE", "SUPPRESSED"}),
    "CUSTOMER": frozenset({"NURTURE", "SUPPRESSED"}),
    "NOT_INTERESTED": frozenset({"NURTURE", "SUPPRESSED"}),
    "NURTURE": frozenset({"QUALIFIED", "WORKING", "ENGAGED", "FOLLOW_UP", "SUPPRESSED"}),
    "SUPPRESSED": frozenset({"NEW", "QUALIFIED", "NURTURE"}),
}

CONTACT_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
    "NOT_CONTACTED": frozenset({"CONTACTED", "SUPPRESSED"}),
    "CONTACTED": frozenset({"CONNECTED", "REPLIED", "SUPPRESSED"}),
    "CONNECTED": frozenset({"REPLIED", "FOLLOW_UP", "SUPPRESSED"}),
    "REPLIED": frozenset({"FOLLOW_UP", "SUPPRESSED"}),
    "FOLLOW_UP": frozenset({"REPLIED", "CONNECTED", "SUPPRESSED"}),
    "SUPPRESSED": frozenset({"NOT_CONTACTED", "CONTACTED"}),
}
class StateTransitionError(ValueError):
    """Raised when an operator requests a state transition outside the contract."""


def validate_state_transition(
    *, entity_type: EntityType, current_state: str, target_state: str, explicit_unsuppress: bool = False
) -> None:
    states = ACCOUNT_STATES if entity_type == "account" else CONTACT_STATES
    transitions = ACCOUNT_TRANSITIONS if entity_type == "account" else CONTACT_TRANSITIONS
    if current_state not in states:
        raise StateTransitionError(f"unknown {entity_type} state: {current_state}")
    if target_state not in states:
        raise StateTransitionError(f"unknown {entity_type} state: {target_state}")
    if current_state == target_state:
        raise StateTransitionError("state is already set to the requested value")
    if current_state == "SUPPRESSED" and not explicit_unsuppress:
        raise StateTransitionError("leaving SUPPRESSED requires explicit unsuppress authorization")
    if target_state not in transitions[current_state]:
        raise StateTransitionError(
            f"invalid {entity_type} transition: {current_state} -> {target_state}"
        )
