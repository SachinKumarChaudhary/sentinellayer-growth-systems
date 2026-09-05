from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from .tracking import build_tracking_event, classify_traffic, default_confidence
from .tracking_repository import TrackingRepository


@dataclass(frozen=True)
class IngestionResult:
    accepted: bool
    event_id: UUID | None
    traffic_classification: str
    destination_url: str | None = None


class TrackingService:
    """Trusted first-party service boundary for tracking ingestion."""

    def __init__(self, repository: TrackingRepository) -> None:
        self.repository = repository

    def ingest_link_request(
        self,
        *,
        public_token: str,
        environment: str,
        source_system: str,
        correlation_id: str,
        user_agent: str | None,
        method: str = "GET",
        accept: str | None = None,
        sec_ch_ua: str | None = None,
        sec_fetch_mode: str | None = None,
        referrer: str | None = None,
        ip_hash: str | None = None,
        session_id: str | None = None,
        occurred_at: datetime | None = None,
        idempotency_key: str | None = None,
    ) -> IngestionResult:
        target = self.repository.resolve_trackable_link(public_token, now=occurred_at)
        if target is None:
            return IngestionResult(False, None, "unknown", None)

        traffic = classify_traffic(
            user_agent=user_agent,
            method=method,
            accept=accept,
            sec_ch_ua=sec_ch_ua,
            sec_fetch_mode=sec_fetch_mode,
        )
        event_time = (occurred_at or datetime.now(UTC)).astimezone(UTC)
        confidence = default_confidence(traffic.classification)

        event = build_tracking_event(
            event_type="link_clicked",
            source_system=source_system,
            environment=environment,
            correlation_id=correlation_id,
            account_id=target.account_id,
            person_id=str(target.person_id) if target.person_id is not None else None,
            campaign_id=target.campaign_id,
            send_id=target.send_id,
            confidence=confidence,
            occurred_at=event_time,
            payload={
                "link_id": target.token,
                "link_type": target.link_type,
                "traffic_classification": traffic.classification,
            },
        )

        inserted = self.repository.record_link_event(
            event_id=event.event_id,
            link_id=target.token,
            event=event,
            user_agent=user_agent,
            referrer=referrer,
            ip_hash=ip_hash,
            link_type=target.link_type,
            automation_classification=traffic.classification,
            automation_reason=traffic.reason,
            source_event_id=None,
            ingest_key=(f"link:{target.token}:{idempotency_key}" if idempotency_key else None),
        )

        if session_id:
            self.repository.upsert_session(
                session_id=session_id,
                person_id=target.person_id,
                account_id=target.account_id,
                campaign_id=target.campaign_id,
                send_id=target.send_id,
                occurred_at=event_time,
                metadata={"last_link_type": target.link_type},
            )

        return IngestionResult(inserted, event.event_id, traffic.classification, target.destination_url)

    def ingest_behavior_event(
        self,
        *,
        event_type: str,
        environment: str,
        source_system: str,
        correlation_id: str,
        payload: Mapping[str, Any] | None = None,
        account_id: str | None = None,
        person_id: str | None = None,
        campaign_id: str | None = None,
        send_id: str | None = None,
        session_id: str | None = None,
        user_agent: str | None = None,
        occurred_at: datetime | None = None,
    ) -> IngestionResult:
        traffic = classify_traffic(user_agent=user_agent)
        event = build_tracking_event(
            event_type=event_type,
            environment=environment,
            source_system=source_system,
            correlation_id=correlation_id,
            payload=payload,
            account_id=account_id,
            person_id=person_id,
            campaign_id=campaign_id,
            send_id=send_id,
            confidence=default_confidence(traffic.classification),
            occurred_at=occurred_at,
        )
        inserted = self.repository.record_behavioral_event(
            event,
            session_id=session_id,
            automation_classification=traffic.classification,
            automation_reason=traffic.reason,
            ingest_key=f"behavior:{event.event_type}:{correlation_id}:{event.event_id}",
        )
        if session_id:
            self.repository.upsert_session(
                session_id=session_id,
                person_id=int(person_id) if person_id and person_id.isdigit() else None,
                account_id=account_id,
                campaign_id=campaign_id,
                send_id=send_id,
                occurred_at=occurred_at,
            )
        return IngestionResult(inserted, event.event_id, traffic.classification)
