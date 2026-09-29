"""CRM MVP domain contracts and deterministic operator workflow primitives."""

from .state import (
    ACCOUNT_STATES,
    CONTACT_STATES,
    StateTransitionError,
    validate_state_transition,
)

__all__ = [
    "ACCOUNT_STATES",
    "CONTACT_STATES",
    "StateTransitionError",
    "validate_state_transition",
]
