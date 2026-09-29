"""CRM MVP domain contracts and deterministic operator workflow primitives."""

from .read_models import CRMReadModelRepository
from .repository import CRMRepository
from .service import CRMActor, CRMService, CRMServiceError
from .state import (
    ACCOUNT_STATES,
    CONTACT_STATES,
    StateTransitionError,
    validate_state_transition,
)

__all__ = [
    "ACCOUNT_STATES",
    "CONTACT_STATES",
    "CRMActor",
    "CRMReadModelRepository",
    "CRMRepository",
    "CRMService",
    "CRMServiceError",
    "StateTransitionError",
    "validate_state_transition",
]
