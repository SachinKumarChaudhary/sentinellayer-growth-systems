from __future__ import annotations

from datetime import UTC, datetime

from sentinellayer_growth_engine.phase2.observability import TinyFishAttemptRecorder
from sentinellayer_growth_engine.provider_resilience import TinyFishRequestTelemetry


class FakeRepository:
    def __init__(self) -> None:
        self.records = []

    def persist_provider_attempt(self, record: object) -> None:
        self.records.append(record)


def _telemetry(
    *,
    status: str,
    failure_code: str | None = None,
    retry_count: int = 0,
) -> TinyFishRequestTelemetry:
    now = datetime(2026, 9, 27, 16, 0, tzinfo=UTC)
    return TinyFishRequestTelemetry(
        operation="search",
        request_fingerprint="a" * 64,
        started_at=now,
        finished_at=now,
        latency_ms=42,
        quota_units=1,
        attempts=retry_count + 1,
        retry_count=retry_count,
        cache_hit=status == "CACHE_HIT",
        status=status,
        http_status=429 if failure_code == "RATE_LIMIT" else 200,
        failure_code=failure_code,
    )


def test_tinyfish_attempt_recorder_maps_success_and_preserves_context() -> None:
    repository = FakeRepository()
    recorder = TinyFishAttemptRecorder(
        repository, run_id="run-1", lead_id="lead-1", mission_id="mission-1"
    )

    record = recorder.record(
        _telemetry(status="SUCCEEDED"),
        request_parameters={"purpose": "entity identity"},
        result_count=4,
        quota_state={"remaining": 29},
        raw_artifact_ref="artifact://raw/1",
        raw_artifact_hash="b" * 64,
        evidence_ids=["evidence-1", "evidence-2"],
        escalation_reason="initial_search",
        information_gain_estimate=0.75,
    )

    assert record.status == "SUCCEEDED"
    assert record.lead_id == "lead-1"
    assert record.mission_id == "mission-1"
    assert record.request_payload["purpose"] == "entity identity"
    assert record.quota_state["remaining"] == 29
    assert record.evidence_ids == ["evidence-1", "evidence-2"]
    assert repository.records == [record]


def test_tinyfish_attempt_recorder_maps_cache_hits_to_cached() -> None:
    repository = FakeRepository()
    recorder = TinyFishAttemptRecorder(repository, run_id="run-1", lead_id="lead-1")

    record = recorder.record(_telemetry(status="CACHE_HIT"))

    assert record.status == "CACHED"
    assert record.error_code is None
    assert record.retry_count == 0


def test_tinyfish_attempt_recorder_maps_rate_limits_to_rate_limited() -> None:
    repository = FakeRepository()
    recorder = TinyFishAttemptRecorder(repository, run_id="run-1", lead_id="lead-1")

    record = recorder.record(
        _telemetry(status="FAILED", failure_code="RATE_LIMIT", retry_count=2)
    )

    assert record.status == "RATE_LIMITED"
    assert record.error_code == "RATE_LIMIT"
    assert record.http_status == 429
    assert record.retry_count == 2
