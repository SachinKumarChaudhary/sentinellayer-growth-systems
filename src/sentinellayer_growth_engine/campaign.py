from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parseaddr
from typing import Any, Mapping

from .contracts import validate_rendered_send_treatment

_PLACEHOLDER = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_.-]*)\s*}}")


class CampaignRenderError(ValueError):
    """Raised when a campaign treatment cannot be rendered safely."""


@dataclass(frozen=True)
class RenderContext:
    enrollment_id: str
    campaign_id: str
    person_id: str
    account_id: str
    sequence_step_id: str
    strategy_version_id: str
    offer_version_id: str
    message_version_id: str
    cta_version_id: str
    sequence_version_id: str
    recipient_email: str
    personalization: Mapping[str, Any]
    evidence: Mapping[str, Any]
    asset: Mapping[str, Any] | None = None
    experiment_id: str | None = None
    experiment_variant_id: str | None = None
    reply_to: str | None = None


@dataclass(frozen=True)
class RenderedMessage:
    subject: str
    body_text: str


def _lookup(values: Mapping[str, Any], key: str) -> Any:
    current: Any = values
    for part in key.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise CampaignRenderError(f"missing personalization variable: {key}")
        current = current[part]
    if current is None or (isinstance(current, str) and not current.strip()):
        raise CampaignRenderError(f"empty personalization variable: {key}")
    return current


def _render_template(template: str, values: Mapping[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        return str(_lookup(values, match.group(1)))

    rendered = _PLACEHOLDER.sub(replace, template)
    unresolved = _PLACEHOLDER.findall(rendered)
    if unresolved:
        raise CampaignRenderError(
            "unresolved personalization variables: " + ", ".join(sorted(set(unresolved)))
        )
    return rendered


def _required_evidence(requirements: Mapping[str, Any]) -> list[str]:
    raw = requirements.get("required", [])
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(item, str) and item.strip() for item in raw):
        raise CampaignRenderError(
            "evidence_requirements.required must be a list of non-empty strings"
        )
    return raw


def _require_evidence(requirements: Mapping[str, Any], evidence: Mapping[str, Any]) -> None:
    for key in _required_evidence(requirements):
        if key not in evidence:
            raise CampaignRenderError(f"required evidence missing: {key}")
        value = evidence[key]
        if value is None or (isinstance(value, str) and not value.strip()):
            raise CampaignRenderError(f"required evidence empty: {key}")


def _validate_email(value: str, field: str) -> str:
    address = parseaddr(value)[1]
    if not address or "@" not in address or address.startswith("@") or address.endswith("@"):
        raise CampaignRenderError(f"invalid {field}")
    return address


class TreatmentRenderer:
    """Render an immutable campaign treatment without performing delivery."""

    ALLOWED_VERSION_STATUSES = frozenset({"reviewed", "testing", "active"})

    def render(
        self,
        *,
        context: RenderContext,
        message_version: Mapping[str, Any],
        cta_version: Mapping[str, Any],
    ) -> dict[str, Any]:
        self._validate_version("message", message_version)
        self._validate_version("CTA", cta_version)

        recipient = _validate_email(context.recipient_email, "recipient_email")
        if context.reply_to is not None:
            _validate_email(context.reply_to, "reply_to")

        requirements = message_version.get("evidence_requirements", {})
        if not isinstance(requirements, Mapping):
            raise CampaignRenderError("message evidence_requirements must be an object")
        _require_evidence(requirements, context.evidence)

        cta_label = cta_version.get("label")
        if not isinstance(cta_label, str) or not cta_label.strip():
            raise CampaignRenderError("CTA label is required")

        values = dict(context.personalization)
        values.setdefault("cta", {})
        if not isinstance(values["cta"], Mapping):
            raise CampaignRenderError("personalization key 'cta' must be an object when supplied")
        values["cta"] = {**values["cta"], "label": cta_label, "target": cta_version.get("target") or ""}

        subject_template = message_version.get("subject_template")
        body_template = message_version.get("body_template")
        if not isinstance(subject_template, str) or not subject_template.strip():
            raise CampaignRenderError("message subject_template is required")
        if not isinstance(body_template, str) or not body_template.strip():
            raise CampaignRenderError("message body_template is required")

        subject = _render_template(subject_template, values).strip()
        body_text = _render_template(body_template, values).strip()
        if not subject or not body_text:
            raise CampaignRenderError("rendered message cannot be empty")

        payload: dict[str, Any] = {
            "schema_version": "1.0",
            "enrollment_id": context.enrollment_id,
            "campaign_id": context.campaign_id,
            "person_id": context.person_id,
            "account_id": context.account_id,
            "sequence_step_id": context.sequence_step_id,
            "strategy_version_id": context.strategy_version_id,
            "offer_version_id": context.offer_version_id,
            "message_version_id": context.message_version_id,
            "cta_version_id": context.cta_version_id,
            "sequence_version_id": context.sequence_version_id,
            "experiment_id": context.experiment_id,
            "experiment_variant_id": context.experiment_variant_id,
            "recipient_email": recipient,
            "subject": subject,
            "body_text": body_text,
            "headers": {
                "X-SL-Campaign-Id": context.campaign_id,
                "X-SL-Enrollment-Id": context.enrollment_id,
                "X-SL-Message-Version": context.message_version_id,
            },
            "asset": dict(context.asset) if context.asset is not None else None,
            "personalization": dict(context.personalization),
            "reply_to": context.reply_to,
            "rendered_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            return validate_rendered_send_treatment(payload)
        except Exception as exc:
            raise CampaignRenderError(str(exc)) from exc

    @classmethod
    def _validate_version(cls, name: str, record: Mapping[str, Any]) -> None:
        status = record.get("status")
        if status not in cls.ALLOWED_VERSION_STATUSES:
            raise CampaignRenderError(f"{name} version is not renderable: status={status!r}")
        if name == "message" and record.get("qa_status") != "approved":
            raise CampaignRenderError("message version is not QA approved")
