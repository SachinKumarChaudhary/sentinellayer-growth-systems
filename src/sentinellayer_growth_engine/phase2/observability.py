from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..provider_resilience import TinyFishRequestTelemetry
from .repository import Phase2Repository
from .storage import ProviderAttemptRecord


class TinyFishAttemptRecorder:
    """Bridge provider telemetry into the immutable Phase 2 attempt ledger.

    This component only records execution evidence. It cannot mutate an
    EntityResolutionDecision or promote provider output into business truth.
    """

    def __init__(
        self,
        repository: Phase2Repository,
        *,
        run_id: str,
        lead_id: str,
        mission_id: str | None = None,
    ) -> None:
        self._repository = repository
        self._run_id = run_id
        self._lead_id = lead_id
        self._mission_id = mission_id

    def record(
        self,
        telemetry: TinyFishRequestTelemetry,
        *,
        request_parameters: Mapping[str, Any] | None = None,
        provider_request_id: str | None = None,
        result_count: int | None = None,
        cost_units: float | None = None,
        quota_state: Mapping[str, Any] | None = None,
        raw_artifact_ref: str | None = None,
        raw_artifact_hash: str | None = None,
        evidence_ids: list[str] | None = None,
        escalation_reason: str | None = None,
        information_gain_estimate: float | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> ProviderAttemptRecord:
        status, failure_code = self._map_status(telemetry)

        record = ProviderAttemptRecord(
            run_id=self._run_id,
            lead_id=self._lead_id,
            mission_id=self._mission_id,
            provider="tinyfish",
            operation=telemetry.operation,
            request_fingerprint=telemetry.request_fingerprint,
            request_payload=dict(request_parameters or {}),
            status=status,
            provider_request_id=provider_request_id,
            http_status=telemetry.http_status,
            retry_count=telemetry.retry_count,
            result_count=result_count,
            latency_ms=telemetry.latency_ms,
            cost_units=cost_units,
            error_code=failure_code,
            error_message=None,
            quota_state={
                "quota_units": telemetry.quota_units,
                "attempts": telemetry.attempts,
                "cache_hit": telemetry.cache_hit,
                **dict(quota_state or {}),
            },
            raw_artifact_ref=raw_artifact_ref,
            raw_artifact_hash=raw_artifact_hash,
            evidence_ids=list(evidence_ids or []),
            escalation_reason=escalation_reason,
            information_gain_estimate=information_gain_estimate,
            started_at=telemetry.started_at,
            completed_at=telemetry.finished_at,
            metadata={
                "telemetry_status": telemetry.status,
                **dict(metadata or {}),
            },
        )
        self._repository.persist_provider_attempt(record)
        return record

    @staticmethod
    def _map_status(
        telemetry: TinyFishRequestTelemetry,
    ) -> tuple[str, str | None]:
        if telemetry.status == "CACHE_HIT":
            return "CACHED", None
        if telemetry.status == "SUCCEEDED":
            return "SUCCEEDED", None
        if telemetry.failure_code in {"RATE_LIMIT", "QUOTA_EXHAUSTED"}:
            return "RATE_LIMITED", telemetry.failure_code
        return "FAILED", telemetry.failure_code
