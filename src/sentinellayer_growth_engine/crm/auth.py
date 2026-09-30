from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

from ..config import Settings


class CRMAuthenticationError(RuntimeError):
    pass


@dataclass(frozen=True)
class SupabaseAuthVerifier:
    settings: Settings
    timeout_seconds: float = 5.0

    def verify_bearer_token(self, token: str) -> UUID | None:
        if not self.settings.supabase_url or not self.settings.supabase_service_key:
            raise CRMAuthenticationError("Supabase authentication is not configured")
        token = token.strip()
        if not token:
            return None
        url = self.settings.supabase_url.rstrip("/") + "/auth/v1/user"
        request = Request(
            url,
            headers={
                "apikey": self.settings.supabase_service_key,
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": "SentinelLayer-CRM/1",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            if isinstance(exc, HTTPError) and exc.code in (401, 403):
                return None
            raise CRMAuthenticationError("Supabase auth verification failed") from exc
        user_id = payload.get("id") if isinstance(payload, dict) else None
        try:
            return UUID(str(user_id)) if user_id else None
        except ValueError:
            raise CRMAuthenticationError("Supabase auth response contained invalid user id")


def bearer_from_headers(headers: dict[str, str]) -> str | None:
    value = headers.get("authorization", "").strip()
    if not value:
        return None
    scheme, _, token = value.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()
