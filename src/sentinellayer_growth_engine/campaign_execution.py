from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

from .campaign import RenderContext, TreatmentRenderer
from .campaign_db import CampaignDatabase
from .mail_handoff import CampaignMailHandoff


class CampaignExecutionError(ValueError):
    """Raised when a claimed campaign step cannot safely reach Mail."""


class CampaignExecutionOrchestrator:
    """Claim -> render -> persist a campaign step without delivery side effects."""

    def __init__(
        self,
        campaign_db: CampaignDatabase,
        renderer: TreatmentRenderer | None = None,
        mail_handoff: CampaignMailHandoff | None = None,
    ) -> None:
        self.campaign_db = campaign_db
        self.renderer = renderer or TreatmentRenderer()
        self.mail_handoff = mail_handoff or CampaignMailHandoff()

    def _claim_and_build(
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
        asset: Mapping[str, Any] | None,
        experiment_id: str | None,
        experiment_variant_id: str | None,
        reply_to: str | None,
    ) -> tuple[dict[str, Any], str, int, int, datetime]:
        claim = self.campaign_db.claim_step(enrollment_id, worker_id)
        if claim is None:
            raise CampaignExecutionError("campaign step is not currently claimable")

        token = str(claim["step_claim_token"])
        step_no = int(claim["step_no"])
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
                personalization={**personalization, **evidence},
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
            request = self.mail_handoff.build_send_request(
                treatment=treatment,
                mailbox_id=mailbox_id,
                scheduled_at=scheduled_at,
            )
            return request, token, step_no, int(claim.get("delay_days", 0)), scheduled_at
        except Exception:
            self.campaign_db.release_step(enrollment_id, token)
            raise

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
        request, _token, _step_no, _delay_days, _scheduled_at = self._claim_and_build(
            enrollment_id=enrollment_id,
            worker_id=worker_id,
            mailbox_id=mailbox_id,
            scheduled_at=scheduled_at,
            message_version=message_version,
            cta_version=cta_version,
            personalization=personalization,
            evidence=evidence,
            asset=asset,
            experiment_id=experiment_id,
            experiment_variant_id=experiment_variant_id,
            reply_to=reply_to,
        )
        return request

    def execute(
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
        """Claim, render, persist exactly once, then advance the Campaign step.

        Persistence is idempotent. If step completion fails after the send was
        persisted, lease expiry allows a retry to recover the same send by key
        and then advance the enrollment without creating a second send.
        """
        request, token, step_no, delay_days, scheduled = self._claim_and_build(
            enrollment_id=enrollment_id,
            worker_id=worker_id,
            mailbox_id=mailbox_id,
            scheduled_at=scheduled_at,
            message_version=message_version,
            cta_version=cta_version,
            personalization=personalization,
            evidence=evidence,
            asset=asset,
            experiment_id=experiment_id,
            experiment_variant_id=experiment_variant_id,
            reply_to=reply_to,
        )
        try:
            send = self.campaign_db.enqueue_send_request(request)
            completed = self.campaign_db.complete_step(
                enrollment_id=enrollment_id,
                claim_token=token,
                step_no=step_no,
                next_action_at=scheduled + timedelta(days=delay_days),
            )
            if not completed:
                raise CampaignExecutionError("campaign step completion failed after send persistence")
            return {"send_request": request, "send": send, "status": "queued"}
        except Exception:
            # Once the SendRequest has been persisted, release is harmless if the
            # lease is still owned; a retry is idempotent by send idempotency key.
            self.campaign_db.release_step(enrollment_id, token)
            raise
