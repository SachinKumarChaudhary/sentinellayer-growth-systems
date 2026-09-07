from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

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


@dataclass
class GroqAnalyzer:
    """Groq-backed semantic analyzer with bounded retries and fail-closed output.

    The API key is supplied at call time so secrets remain outside application
    objects and can come from the runtime environment/secret manager.
    """

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
            raise ConversationAnalysisError("Groq API key is required")
        if not body_text.strip() and not subject.strip():
            raise ConversationAnalysisError("message content is required")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")

        payload = {
            "model": self.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Analyze the full inbound sales conversation. Return only JSON matching "
                        "the supplied JSON schema. Extract semantic intent, objections, timing, "
                        "questions, and evidence from the original message. Never invent evidence. "
                        "Explicit opt-out language must set explicit_opt_out=true."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Subject:\n{subject}\n\n"
                        f"Full inbound message:\n{body_text}\n\n"
                        f"Relevant conversation context:\n{conversation_context}"
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

        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        last_error: Exception | None = None
        for attempt in range(self.max_attempts):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                    raw = response.read()
                decoded = json.loads(raw.decode("utf-8"))
                content = decoded["choices"][0]["message"]["content"]
                analysis = json.loads(content)
                return validate_contract("conversation_analysis", analysis)
            except urllib.error.HTTPError as exc:
                last_error = exc
                if not self._retryable_status(exc.code):
                    break
            except (urllib.error.URLError, TimeoutError, OSError, KeyError, IndexError, TypeError, ValueError) as exc:
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
    def _schema() -> dict[str, Any]:
        from pathlib import Path

        path = Path(__file__).resolve().parents[2] / "schemas" / "conversation-analysis.schema.json"
        return json.loads(path.read_text(encoding="utf-8"))
