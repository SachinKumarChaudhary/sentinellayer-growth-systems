from uuid import UUID

from sentinellayer_growth_engine.config import Settings
from sentinellayer_growth_engine.crm.auth import (
    SupabaseAuthVerifier,
    bearer_from_headers,
)
from sentinellayer_growth_engine.crm.service import CRMActor, CRMService, CRMServiceError


def test_bearer_parser():
    assert bearer_from_headers({"authorization": "Bearer abc"}) == "abc"
    assert bearer_from_headers({"authorization": "Basic abc"}) is None
    assert bearer_from_headers({}) is None


def test_supabase_auth_verifier_maps_user_id(monkeypatch):
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def read(self):
            return b'{"id":"11111111-1111-4111-8111-111111111111"}'

    def fake_urlopen(request, timeout):
        assert request.full_url.endswith("/auth/v1/user")
        assert request.get_header("Authorization") == "Bearer access-token"
        return Response()

    monkeypatch.setattr(
        "sentinellayer_growth_engine.crm.auth.urlopen",
        fake_urlopen,
    )
    settings = Settings(
        database_url="postgresql://unused",
        SUPABASE_URL="https://example.supabase.co",
        SUPABASE_SERVICE_KEY="secret-not-printed",
    )
    verifier = SupabaseAuthVerifier(settings)
    assert verifier.verify_bearer_token("access-token") == UUID(
        "11111111-1111-4111-8111-111111111111"
    )


def test_service_authorize_requires_membership():
    class DeniedRepo:
        def get_user_access(self, **kwargs):
            return None

    service = CRMService(write_repo=DeniedRepo(), read_repo=object())
    actor = CRMActor(user_id=UUID("11111111-1111-4111-8111-111111111111"))
    try:
        service.authorize(actor)
    except CRMServiceError as exc:
        assert exc.code == "FORBIDDEN"
    else:
        raise AssertionError("expected membership rejection")


def test_service_authorize_reviewer_cannot_mutate():
    class ReviewerRepo:
        def get_user_access(self, **kwargs):
            return {"role": "REVIEWER", "active": True}

    service = CRMService(write_repo=ReviewerRepo(), read_repo=object())
    actor = CRMActor(user_id=UUID("11111111-1111-4111-8111-111111111111"))
    try:
        service.authorize(actor, mutation=True)
    except CRMServiceError as exc:
        assert exc.code == "FORBIDDEN"
    else:
        raise AssertionError("expected read-only role rejection")
