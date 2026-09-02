from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


from .contracts import ContractValidationError, validate_rendered_send_treatment, validate_send_request

class CampaignMailHandoffError(ValueError):
    """Raised when Campaign cannot safely construct a Mail request."""


class CampaignMailHandoff:
    """Build a validated SendRequest without performing delivery.

    Mail owns send persistence, claiming, SMTP/provider execution, retries and
    provider outcomes. Campaign only supplies the immutable treatment and the
    routing information explicitly required by the shared contract.
    """

    def build_send_request(
        self,
        *,
        treatment: Mapping[str, Any],
        mailbox_id: str,
        scheduled_at: datetime,
        send_id: str | None = None,
        idempotency_key: str | None = None,
        schema_version: str = "1.0",
    ) -> dict[str, Any]:
        try:
            UUID(mailbox_id)
        except (ValueError, AttributeError, TypeError) as exc:
            raise CampaignMailHandoffError("mailbox_id must be a UUID") from exc
        if scheduled_at.tzinfo is None:
            raise CampaignMailHandoffError("scheduled_at must be timezone-aware")

        try:
            frozen = validate_rendered_send_treatment(treatment)
        except ContractValidationError as exc:
            raise CampaignMailHandoffError(f"invalid treatment: {exc}") from exc

        if send_id is None:
            send_id = str(uuid4())
        try:
            UUID(send_id)
        except (ValueError, AttributeError, TypeError) as exc:
            raise CampaignMailHandoffError("send_id must be a UUID") from exc

        key = idempotency_key or self._default_idempotency_key(frozen)
        if not key.strip():
            raise CampaignMailHandoffError("idempotency_key must not be empty")

        request = {
            "schema_version": schema_version,
            "send_id": send_id,
            "idempotency_key": key,
            "campaign_id": frozen["campaign_id"],
            "person_id": frozen["person_id"],
            "sequence_step_id": frozen["sequence_step_id"],
            "mailbox_id": mailbox_id,
            "scheduled_at": scheduled_at.isoformat(),
            "treatment": frozen,
        }
        try:
            return validate_send_request(request)
        except ContractValidationError as exc:
            raise CampaignMailHandoffError(f"invalid send request: {exc}") from exc

    @staticmethod
    def _default_idempotency_key(treatment: Mapping[str, Any]) -> str:
        return ":".join(
            (
                "campaign-send",
                str(treatment["campaign_id"]),
                str(treatment["person_id"]),
                str(treatment["sequence_step_id"]),
            )
        )
