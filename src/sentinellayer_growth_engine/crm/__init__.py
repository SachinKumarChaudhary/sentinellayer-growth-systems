"""CRM MVP domain contracts and deterministic operator workflow primitives."""

from .auth import CRMAuthenticationError, SupabaseAuthVerifier, bearer_from_headers
from .http import CRMHTTPApplication
from .migration import (
    OperationalSheetRow,
    ParsedStatus,
    SourceSnapshot,
    build_operational_sheet_staged_rows,
    build_staged_rows,
    normalize_domain,
    normalize_email,
    normalize_linkedin,
    normalize_phone,
    operational_sheet_profile,
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
    "CRMAuthenticationError",
    "CRMHTTPApplication",
    "CRMReadModelRepository",
    "CRMRepository",
    "CRMService",
    "CRMServiceError",
    "OperationalSheetRow",
    "ParsedStatus",
    "SourceSnapshot",
    "build_operational_sheet_staged_rows",
    "build_staged_rows",
    "normalize_domain",
    "normalize_email",
    "normalize_linkedin",
    "normalize_phone",
    "operational_sheet_profile",
    "parse_lead_status",
    "profile_source",
    "reconciliation_is_complete",
    "SupabaseAuthVerifier",
    "bearer_from_headers",
    "StateTransitionError",
    "validate_state_transition",
]
