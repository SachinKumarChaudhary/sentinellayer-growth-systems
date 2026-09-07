from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from typing import Any, Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .contracts import validate_contract


class ConversationAnalysisError(RuntimeError):
    """Raised when semantic conversation analysis cannot be completed safely."""


class ConversationAnalyzer(Protocol):
    def analyze(
        self,
        *,
        subject: str,
        body_text: str,
        conversation_context: str = "",
    ) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class GroqAnalyzer:
    api_key: str
    model: str = "openai/gpt-oss-20b"
    endpoint: str = "https://api.groq.com/openai/v1/chat/completions"
    timeout_seconds: float = 20.0
    max_attempts: int = 4
    base_backoff_seconds: float = 0.5

    def analyze(
        self,
        *,
        subject: str,
        body_text: str,
        conversation_context: str = "",
    ) -> dict[str, Any]:
        if not self.api_key.strip():
            raise ValueError("api_key must not be empty")
        if not (subject.strip() or body_text.strip()):
            raise ValueError("subject or body_text must not be empty")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be positive")

        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Analyze the inbound conversation semantically. Determine the primary intent, "
                        "secondary intents, objections, timing, questions, and evidence. Use the full "
                        "message and supplied context. Never invent evidence. Set explicit_opt_out true "
                        "only when the message explicitly asks to stop or unsubscribe. Return only the "
                        "requested structured object."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Subject:\n{subject}\n\nBody:\n{body_text}\n\n"
                        f"Conversation context:\n{conversation_context}"
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "conversation_analysis",
                    "strict": True,
                    "schema": self._schema(),
                },
            },
        }
        data = json.dumps(payload).encode("utf-8")
        last_error: Exception | None = None

        for attempt in range(self.max_attempts):
            request = Request(
                self.endpoint,
                data=data,
                method="POST",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    raw = response.read().decode("utf-8")
                envelope = json.loads(raw)
                content = envelope["choices"][0]["message"]["content"]
                analysis = json.loads(content)
                validate_contract("conversation_analysis", analysis)
                return cast(dict[str, Any], analysis)
            except HTTPError as exc:
                last_error = exc
                if not self._retryable_status(exc.code):
                    detail = self._http_error_detail(exc)
                    raise ConversationAnalysisError(
                        f"Groq analysis rejected with HTTP {exc.code}: {detail}"
                    ) from exc
            except (URLError, TimeoutError, OSError, KeyError, IndexError, TypeError, ValueError) as exc:
                last_error = exc
            if attempt + 1 < self.max_attempts:
                delay = self.base_backoff_seconds * (2**attempt)
                delay *= 0.8 + random.random() * 0.4
                time.sleep(delay)

        raise ConversationAnalysisError("Groq analysis unavailable after bounded retries") from last_error

    @staticmethod
    def _retryable_status(status: int) -> bool:
        return status == 408 or status == 409 or status == 429 or status >= 500

    @staticmethod
    def _http_error_detail(exc: HTTPError) -> str:
        try:
            raw = exc.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            if isinstance(data, dict) and isinstance(data.get("error"), dict):
                error = data["error"]
                parts = []
                for key in ("type", "code", "message"):
                    value = error.get(key)
                    if value:
                        parts.append(f"{key}={str(value)[:300]}")
                return "; ".join(parts) or "provider returned a structured error"
            return raw[:500] or "provider returned an empty error body"
        except (OSError, UnicodeError, ValueError, TypeError):
            return "provider returned an unreadable error body"

    @staticmethod
    def _schema() -> dict[str, Any]:
        from pathlib import Path

        path = Path(__file__).resolve().parents[2] / "schemas" / "conversation-analysis.schema.json"
        return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
