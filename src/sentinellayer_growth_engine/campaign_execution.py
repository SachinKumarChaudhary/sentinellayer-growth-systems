from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any
from uuid import UUID

from .campaign_db import CampaignDatabase
from .campaign import RenderContext, TreatmentRenderer
from .mail_handoff import CampaignMailHandoff, CampaignMailHandoffError


class CampaignExecutionError(ValueError):
    """Raised when a claimed campaign step cannot safely reach Mail."""


class CampaignExecutionOrchestrator:
    """Claim -> render -> hand off a campaign step without delivery side effects."""

    def __init__(
        self,
        campaign_db: CampaignDatabase,
        renderer: TreatmentRenderer | None = None,
        mail_handoff: CampaignMailHandoff | None = None,
    ) -> None:
        self.campaign_db = campaign_db
        self.renderer = renderer or TreatmentRenderer()
        self.mail_handoff = mail_handoff or CampaignMailHandoff()

    def build_send_request(
        self,
        *,
        enrollment_id: str,
        worker_id: str,
        mailbox_id: str,
        scheduled_at: datetime,
        message_version: Mapping[str, Any],
        cta_version: Mapping[str, Any],
        personalization: Mapping[str, Any],
        evidence: Mapping[str, Any],
        asset: Mapping[str, Any] | None = None,
        experiment_id: str | None = None,
        experiment_variant_id: str | None = None,
        reply_to: str | None = None,
    ) -> dict[str, Any]:
        claim = self.campaign_db.claim_step(enrollment_id, worker_id)
        if claim is None:
            raise CampaignExecutionError("campaign step is not currently claimable")

        token = str(claim["step_claim_token"])
        try:
            context = RenderContext(
                enrollment_id=str(claim["enrollment_id"]),
                campaign_id=str(claim["campaign_id"]),
                person_id=str(claim["person_id"]),
                account_id=str(claim["account_id"]),
                sequence_step_id=str(claim["sequence_step_id"]),
                strategy_version_id=str(claim["strategy_version_id"]),
                offer_version_id=str(claim["offer_version_id"]),
                message_version_id=str(claim["message_version_id"]),
                cta_version_id=str(claim["cta_version_id"]),
                sequence_version_id=str(claim["sequence_version_id"]),
                recipient_email=str(claim["recipient_email"]),
                personalization=personalization,
                evidence=evidence,
                asset=asset,
                experiment_id=experiment_id,
                experiment_variant_id=experiment_variant_id,
                reply_to=reply_to,
            )
            treatment = self.renderer.render(
                context=context,
                message_version=message_version,
                cta_version=cta_version,
            )
            return self.mail_handoff.build_send_request(
                treatment=treatment,
                mailbox_id=mailbox_id,
                scheduled_at=scheduled_at,
            )
        except Exception:
            self.campaign_db.release_step(enrollment_id, token)
            raise
