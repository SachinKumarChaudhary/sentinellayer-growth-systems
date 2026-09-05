from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from .tracking import TrackingEvent, generate_tracking_token, validate_destination_url


class ConnectionFactory(Protocol):
    def __call__(self) -> psycopg.Connection[Any]:
        ...


@dataclass(frozen=True)
class TrackableTarget:
    token: str
    destination_url: str
    link_type: str
    send_id: str | None
    person_id: int | None
    account_id: str | None
    campaign_id: str | None
    expires_at: datetime | None


@dataclass(frozen=True)
class AssetTarget:
    token: str
    asset_type: str
    asset_url: str
    send_id: str | None
    person_id: int | None
    account_id: str | None
    campaign_id: str | None
    expires_at: datetime | None


class TrackingRepository:
    """Durable PostgreSQL repository for tracking state.

    Browser clients must never use this class directly. It is intended for the
    trusted first-party ingestion/asset service.
    """

    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def record_behavioral_event(
        self,
        event: TrackingEvent,
        *,
        session_id: str | None = None,
        path: str | None = None,
        automation_classification: str = "unknown",
        automation_reason: str | None = None,
        source_event_id: str | None = None,
        ingest_key: str | None = None,
    ) -> bool:
        """Persist a behavioral event idempotently. Return True when inserted."""
        payload = event.as_contract()
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into tracking.behavioral_events (
                    id, account_id, person_id, campaign_id, send_id,
                    session_id, event_type, event_name, occurred_at, path,
                    metadata, correlation_id, causation_id, confidence,
                    automation_classification, automation_reason,
                    source_event_id, ingest_key
                ) values (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                on conflict do nothing
                returning id
                """,
                (
                    UUID(payload["event_id"]),
                    payload["account_id"],
                    payload["person_id"],
                    payload["campaign_id"],
                    payload["send_id"],
                    session_id,
                    payload["event_type"],
                    payload["event_type"],
                    payload["occurred_at"],
                    path,
                    payload["payload"],
                    payload["correlation_id"],
                    payload["causation_id"],
                    payload["confidence"],
                    automation_classification,
                    automation_reason,
                    source_event_id,
                    ingest_key,
                ),
            )
            return cur.fetchone() is not None

    def record_link_event(
        self,
        *,
        event_id: UUID,
        link_id: str,
        event: TrackingEvent,
        user_agent: str | None,
        referrer: str | None,
        ip_hash: str | None,
        link_type: str,
        automation_classification: str = "unknown",
        automation_reason: str | None = None,
        source_event_id: str | None = None,
        ingest_key: str | None = None,
    ) -> bool:
        payload = event.as_contract()
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into tracking.link_events (
                    id, send_id, person_id, account_id, campaign_id,
                    link_id, occurred_at, user_agent, referrer, ip_hash,
                    metadata, correlation_id, causation_id, confidence,
                    automation_classification, automation_reason,
                    source_event_id, ingest_key, link_type
                ) values (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                on conflict do nothing
                returning id
                """,
                (
                    event_id,
                    payload["send_id"],
                    payload["person_id"],
                    payload["account_id"],
                    payload["campaign_id"],
                    link_id,
                    payload["occurred_at"],
                    user_agent,
                    referrer,
                    ip_hash,
                    payload["payload"],
                    payload["correlation_id"],
                    payload["causation_id"],
                    payload["confidence"],
                    automation_classification,
                    automation_reason,
                    source_event_id,
                    ingest_key,
                    link_type,
                ),
            )
            return cur.fetchone() is not None

    def upsert_session(
        self,
        *,
        session_id: str,
        person_id: int | None,
        account_id: str | None,
        campaign_id: str | UUID | None,
        send_id: str | UUID | None,
        occurred_at: datetime | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        now = (occurred_at or datetime.now(UTC)).astimezone(UTC)
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into tracking.sessions (
                    session_id, person_id, account_id, campaign_id, send_id,
                    first_seen_at, last_seen_at, metadata
                ) values (%s, %s, %s, %s, %s, %s, %s, %s)
                on conflict (session_id) do update
                set person_id = coalesce(excluded.person_id, tracking.sessions.person_id),
                    account_id = coalesce(excluded.account_id, tracking.sessions.account_id),
                    campaign_id = coalesce(excluded.campaign_id, tracking.sessions.campaign_id),
                    send_id = coalesce(excluded.send_id, tracking.sessions.send_id),
                    last_seen_at = greatest(tracking.sessions.last_seen_at, excluded.last_seen_at),
                    metadata = tracking.sessions.metadata || excluded.metadata
                """,
                (session_id, person_id, account_id, campaign_id, send_id, now, now, dict(metadata or {})),
            )

    def create_trackable_link(
        self,
        *,
        destination_url: str,
        link_type: str = "asset",
        send_id: str | None = None,
        person_id: int | None = None,
        account_id: str | None = None,
        campaign_id: str | None = None,
        expires_at: datetime | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> str:
        validate_destination_url(destination_url)
        token = generate_tracking_token()
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into tracking.trackable_links (
                    public_token, send_id, person_id, account_id, campaign_id,
                    link_type, destination_url, expires_at, metadata
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                returning public_token
                """,
                (token, send_id, person_id, account_id, campaign_id, link_type,
                 destination_url, expires_at, dict(metadata or {})),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("failed to create trackable link")
            return str(row[0])

    def resolve_trackable_link(self, token: str, *, now: datetime | None = None) -> TrackableTarget | None:
        now_utc = (now or datetime.now(UTC)).astimezone(UTC)
        with self._connection_factory() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select public_token, destination_url, link_type, send_id, person_id,
                       account_id, campaign_id, expires_at
                from tracking.trackable_links
                where public_token = %s
                  and revoked_at is null
                  and (expires_at is null or expires_at > %s)
                """,
                (token, now_utc),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return TrackableTarget(
            token=str(row["public_token"]),
            destination_url=str(row["destination_url"]),
            link_type=str(row["link_type"]),
            send_id=str(row["send_id"]) if row["send_id"] is not None else None,
            person_id=int(row["person_id"]) if row["person_id"] is not None else None,
            account_id=str(row["account_id"]) if row["account_id"] is not None else None,
            campaign_id=str(row["campaign_id"]) if row["campaign_id"] is not None else None,
            expires_at=row["expires_at"],
        )

    def create_asset_token(
        self,
        *,
        asset_type: str,
        asset_url: str,
        send_id: str | None = None,
        person_id: int | None = None,
        account_id: str | None = None,
        campaign_id: str | None = None,
        expires_at: datetime | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> str:
        validate_destination_url(asset_url)
        token = generate_tracking_token()
        with self._connection_factory() as conn, conn.cursor() as cur:
            cur.execute(
                """
                insert into tracking.asset_tokens (
                    public_token, send_id, person_id, account_id, campaign_id,
                    asset_type, asset_url, expires_at, metadata
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                returning public_token
                """,
                (token, send_id, person_id, account_id, campaign_id, asset_type,
                 asset_url, expires_at, dict(metadata or {})),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("failed to create asset token")
            return str(row[0])

    def resolve_asset_token(self, token: str, *, now: datetime | None = None) -> AssetTarget | None:
        now_utc = (now or datetime.now(UTC)).astimezone(UTC)
        with self._connection_factory() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select public_token, asset_type, asset_url, send_id, person_id,
                       account_id, campaign_id, expires_at
                from tracking.asset_tokens
                where public_token = %s
                  and revoked_at is null
                  and (expires_at is null or expires_at > %s)
                """,
                (token, now_utc),
            )
            row = cur.fetchone()
        if row is None:
            return None
        return AssetTarget(
            token=str(row["public_token"]),
            asset_type=str(row["asset_type"]),
            asset_url=str(row["asset_url"]),
            send_id=str(row["send_id"]) if row["send_id"] is not None else None,
            person_id=int(row["person_id"]) if row["person_id"] is not None else None,
            account_id=str(row["account_id"]) if row["account_id"] is not None else None,
            campaign_id=str(row["campaign_id"]) if row["campaign_id"] is not None else None,
            expires_at=row["expires_at"],
        )
