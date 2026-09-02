from __future__ import annotations

import string
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import UUID

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_VERSION = "1.0"
RENDERABLE_STATUSES = frozenset({"reviewed", "testing", "active"})


class TreatmentRenderingError(ValueError):
    """Raised when a treatment cannot be rendered safely."""


@dataclass(frozen=True)
class RenderContext:
    enrollment_id: str
    campaign_id: str
    person_id: str
    account_id: str
    recipient_email: str
    strategy_version_id: str
    offer_version_id: str
    sequence_version_id: str
    experiment_id: str | None = None
    experiment_variant_id: str | None = None
    evidence: Mapping[str, Any] | None = None
    personalization: Mapping[str, Any] | None = None
    reply_to: str | None = None


class TreatmentRenderer:
    """Render one frozen campaign step into the shared send-treatment shape.

    Template syntax is Python's standard {field} syntax. Only fields present
    in the frozen personalization context are available; attribute/index
    traversal is rejected by the renderer.
    """

    def __init__(self, schema: Mapping[str, Any]) -> None:
        self._validator = Draft202012Validator(schema, format_checker=FormatChecker())

    @staticmethod
    def _render(template: str, values: Mapping[str, Any], field_name: str) -> str:
        if not isinstance(template, str) or not template.strip():
            raise TreatmentRenderingError(f"{field_name} template is empty")
        formatter = string.Formatter()
        parts: list[str] = []
        try:
            for literal, field, spec, conversion in formatter.parse(template):
                parts.append(literal)
                if field is None:
                    continue
                if any(ch in field for ch in ".[]") or not field:
                    raise TreatmentRenderingError(f"{field_name} contains an unsupported template variable")
                if field not in values:
                    raise TreatmentRenderingError(f"{field_name} has unresolved variable: {field}")
                if spec or conversion:
                    raise TreatmentRenderingError(f"{field_name} contains unsupported formatting")
                parts.append(str(values[field]))
        except ValueError as exc:
            raise TreatmentRenderingError(f"{field_name} contains an invalid template") from exc
        result = "".join(parts)
        if not result.strip():
            raise TreatmentRenderingError(f"{field_name} rendered empty")
        return result

    @staticmethod
    def _validate_uuid(value: Any, name: str) -> None:
        try:
            UUID(str(value))
        except (ValueError, AttributeError, TypeError) as exc:
            raise TreatmentRenderingError(f"{name} must be a UUID") from exc

    def render(
        self,
        *,
        context: RenderContext,
        strategy_version: Mapping[str, Any],
        offer_version: Mapping[str, Any],
        message_version: Mapping[str, Any],
        cta_version: Mapping[str, Any],
        sequence_step: Mapping[str, Any],
        asset: Mapping[str, Any] | None = None,
        schema_version: str = SCHEMA_VERSION,
        rendered_at: datetime | None = None,
    ) -> dict[str, Any]:
        for value, name in (
            (context.enrollment_id, "enrollment_id"),
            (context.campaign_id, "campaign_id"),
            (sequence_step.get("id"), "sequence_step_id"),
            (context.strategy_version_id, "strategy_version_id"),
            (context.offer_version_id, "offer_version_id"),
            (message_version.get("id"), "message_version_id"),
            (cta_version.get("id"), "cta_version_id"),
            (context.sequence_version_id, "sequence_version_id"),
        ):
            self._validate_uuid(value, name)

        for record, name in (
            (strategy_version, "strategy"),
            (offer_version, "offer"),
            (message_version, "message"),
            (cta_version, "CTA"),
        ):
            if record.get("status") not in RENDERABLE_STATUSES:
                raise TreatmentRenderingError(f"{name} version is not renderable")

        if str(sequence_step.get("sequence_version_id")) != context.sequence_version_id:
            raise TreatmentRenderingError("sequence step/version mismatch")

        evidence = context.evidence or {}
        required_evidence = message_version.get("required_evidence", ())
        if not isinstance(required_evidence, (list, tuple)):
            raise TreatmentRenderingError("message required_evidence must be a list")
        for key in required_evidence:
            if not isinstance(key, str) or key not in evidence or evidence[key] in (None, ""):
                raise TreatmentRenderingError(f"required evidence missing: {key}")

        values = dict(context.personalization or {})
        subject = self._render(message_version.get("subject_template"), values, "subject")
        cta_text = self._render(cta_version.get("wording_template"), values, "CTA")
        body = self._render(message_version.get("body_template"), values | {"cta": cta_text}, "body")

        policy = sequence_step.get("asset_policy", "none")
        if policy == "none" and asset is not None:
            raise TreatmentRenderingError("asset supplied when asset_policy is none")
        if policy in {"required", "loom", "brief", "diagnostic"} and asset is None:
            raise TreatmentRenderingError("required asset missing")

        timestamp = rendered_at or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            raise TreatmentRenderingError("rendered_at must be timezone-aware")

        result: dict[str, Any] = {
            "schema_version": schema_version,
            "enrollment_id": context.enrollment_id,
            "campaign_id": context.campaign_id,
            "person_id": context.person_id,
            "account_id": context.account_id,
            "sequence_step_id": str(sequence_step["id"]),
            "strategy_version_id": context.strategy_version_id,
            "offer_version_id": context.offer_version_id,
            "message_version_id": str(message_version["id"]),
            "cta_version_id": str(cta_version["id"]),
            "sequence_version_id": context.sequence_version_id,
            "experiment_id": context.experiment_id,
            "experiment_variant_id": context.experiment_variant_id,
            "recipient_email": context.recipient_email,
            "subject": subject,
            "body_text": body,
            "headers": {"X-SentinelLayer-Campaign": context.campaign_id},
            "asset": asset,
            "personalization": dict(values),
            "reply_to": context.reply_to,
            "rendered_at": timestamp.isoformat(),
        }
        errors = sorted(self._validator.iter_errors(result), key=lambda e: list(e.path))
        if errors:
            raise TreatmentRenderingError(
                "RenderedSendTreatment schema validation failed: "
                + "; ".join(error.message for error in errors)
            )
        return result
