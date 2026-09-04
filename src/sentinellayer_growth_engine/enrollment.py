from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID


class EnrollmentError(RuntimeError):
    pass


class EnrollmentConflict(EnrollmentError):
    pass


class CampaignNotReady(EnrollmentError):
    pass

@dataclass(frozen=True)
class EnrollmentRequest:
    campaign_id: str
    account_id: str
    person_id: int
    priority: str
    strategy_version_id: str
    offer_version_id: str | None
    sequence_version_id: str
    experiment_variant_id: str | None = None
    enrolled_at: datetime | None = None

class EnrollmentStore(Protocol):
    def validate_campaign(self, campaign_id: str) -> list[dict[str, Any]]: ...
    def find_enrollment(self, campaign_id: str, person_id: int) -> Any | None: ...
    def create_enrollment(self, request: EnrollmentRequest) -> Any: ...

class CampaignEnrollmentService:
    def __init__(self, store: EnrollmentStore) -> None:
        self._store = store

    def enroll(self, request: EnrollmentRequest) -> Any:
        try:
            UUID(request.campaign_id)
        except (ValueError, TypeError, AttributeError) as exc:
            raise EnrollmentError('campaign_id must be a UUID') from exc
        if request.offer_version_id is None:
            raise EnrollmentError('offer_version_id is required by the canonical CampaignEnrollment contract')
        for field, value in (("strategy_version_id", request.strategy_version_id), ("offer_version_id", request.offer_version_id), ("sequence_version_id", request.sequence_version_id)):
            try:
                UUID(value)
            except (ValueError, TypeError, AttributeError) as exc:
                raise EnrollmentError(f'{field} must be a UUID') from exc
        if request.priority not in {'P1', 'P2', 'P3', 'P4'}:
            raise EnrollmentError('invalid priority')
        if not request.account_id:
            raise EnrollmentError('account_id is required')
        if request.person_id <= 0:
            raise EnrollmentError('person_id must be positive')
        errors = self._store.validate_campaign(request.campaign_id)
        if errors:
            raise CampaignNotReady('campaign is not ready: ' + '; '.join(str(e.get('code', 'unknown')) for e in errors))
        existing = self._store.find_enrollment(request.campaign_id, request.person_id)
        if existing is not None:
            same = (existing.strategy_version_id == request.strategy_version_id and
                    existing.offer_version_id == request.offer_version_id and
                    existing.sequence_version_id == request.sequence_version_id and
                    existing.experiment_variant_id == request.experiment_variant_id)
            if same:
                return existing
            raise EnrollmentConflict('person is already enrolled with a different treatment')
        try:
            return self._store.create_enrollment(request)
        except Exception as exc:
            raise EnrollmentConflict('enrollment could not be created safely') from exc