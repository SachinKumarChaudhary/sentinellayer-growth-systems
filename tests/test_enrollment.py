import pytest

from sentinellayer_growth_engine.enrollment import (
    CampaignEnrollmentService,
    CampaignNotReady,
    EnrollmentConflict,
    EnrollmentError,
    EnrollmentRequest,
)


class Store:
    def __init__(self): self.record=None; self.errors=[]; self.created=[]
    def validate_campaign(self, campaign_id): return self.errors
    def find_enrollment(self, campaign_id, person_id): return self.record
    def create_enrollment(self, request): self.created.append(request); return {"id":"new"}

def request(**overrides):
    data={"campaign_id": "11111111-1111-4111-8111-111111111111","account_id":"a1","person_id":7,"priority":"P1","strategy_version_id": "22222222-2222-4222-8222-222222222222","offer_version_id": "33333333-3333-4333-8333-333333333333","sequence_version_id": "44444444-4444-4444-8444-444444444444"}
    data.update(overrides); return EnrollmentRequest(**data)

def test_not_ready_fails_closed():
    s=Store(); s.errors=[{"code":"missing_sequence_version"}]
    with pytest.raises(CampaignNotReady): CampaignEnrollmentService(s).enroll(request())
    assert s.created == []

def test_identical_existing_is_idempotent():
    s=Store(); s.record=type("R",(),{"strategy_version_id":"22222222-2222-4222-8222-222222222222","offer_version_id":"33333333-3333-4333-8333-333333333333","sequence_version_id":"44444444-4444-4444-8444-444444444444","experiment_variant_id":None})()
    assert CampaignEnrollmentService(s).enroll(request()) is s.record

def test_different_existing_treatment_is_conflict():
    s=Store(); s.record=type("R",(),{"strategy_version_id":"old","offer_version_id":"o1","sequence_version_id":"q1","experiment_variant_id":None})()
    with pytest.raises(EnrollmentConflict): CampaignEnrollmentService(s).enroll(request())

def test_invalid_priority_is_rejected():
    with pytest.raises(EnrollmentError, match="invalid priority"):
        CampaignEnrollmentService(Store()).enroll(request(priority="P9"))
