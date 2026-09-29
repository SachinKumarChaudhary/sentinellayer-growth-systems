"""CRM MVP domain contracts and deterministic operator workflow primitives."""

from .http import CRMHTTPApplication
from .migration import (
    ParsedStatus,
    SourceSnapshot,
    build_staged_rows,
    normalize_domain,
    normalize_email,
    normalize_linkedin,
    normalize_phone,
    parse_lead_status,
    profile_source,
    reconciliation_is_complete,
)
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
    "CRMHTTPApplication",
    "CRMReadModelRepository",
    "CRMRepository",
    "CRMService",
    "CRMServiceError",
    "ParsedStatus",
    "SourceSnapshot",
    "build_staged_rows",
    "normalize_domain",
    "normalize_email",
    "normalize_linkedin",
    "normalize_phone",
    "parse_lead_status",
    "profile_source",
    "reconciliation_is_complete",
    "StateTransitionError",
    "validate_state_transition",
]
