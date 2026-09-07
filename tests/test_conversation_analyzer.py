from unittest.mock import patch

import pytest

from sentinellayer_growth_engine.conversation_analyzer import (
    ConversationAnalysisError,
    GroqAnalyzer,
)


def test_groq_analyzer_requires_key():
    with pytest.raises(ConversationAnalysisError, match="API key"):
        GroqAnalyzer(api_key="").analyze(subject="Hi", body_text="Interested")


def test_groq_analyzer_rejects_empty_message():
    analyzer = GroqAnalyzer(api_key="test")
    with pytest.raises(ConversationAnalysisError, match="message content"):
        analyzer.analyze(subject=" ", body_text=" ")


def test_retryable_statuses_are_bounded():
    assert GroqAnalyzer._retryable_status(408)
    assert GroqAnalyzer._retryable_status(429)
    assert GroqAnalyzer._retryable_status(500)
    assert GroqAnalyzer._retryable_status(503)
    assert not GroqAnalyzer._retryable_status(400)
    assert not GroqAnalyzer._retryable_status(401)


def test_groq_analyzer_parses_and_validates_structured_output():
    payload = {
        "choices": [
            {
                "message": {
                    "content": """{
                      "schema_version": "1.0",
                      "primary_intent": "objection",
                      "secondary_intents": ["interested"],
                      "objections": [{
                        "type": "already_have_solution",
                        "evidence": "We already use another platform.",
                        "confidence": 0.94
                      }],
                      "explicit_opt_out": false,
                      "timing_signal": "later",
                      "questions": [],
                      "evidence": [{
                        "text": "We already use another platform.",
                        "reason": "existing solution"
                      }],
                      "confidence": 0.91
                    }"""
                }
            }
        ]
    }

    class Response:
        def read(self):
            import json

            return json.dumps(payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    with (
        patch(
            "sentinellayer_growth_engine.conversation_analyzer.urllib.request.urlopen",
            return_value=Response(),
        ),
        patch(
            "sentinellayer_growth_engine.conversation_analyzer.time.sleep"
        ) as sleeper,
    ):
        result = GroqAnalyzer(api_key="test").analyze(
                subject="Re: pricing",
                body_text="We already use another platform.",
                conversation_context="Previous outbound described Sentinel Layer.",
            )

    assert result["primary_intent"] == "objection"
    assert result["objections"][0]["type"] == "already_have_solution"
    sleeper.assert_not_called()


def test_groq_analyzer_does_not_retry_non_retryable_http_error():
    from urllib.error import HTTPError

    error = HTTPError(
        url="https://api.groq.com/openai/v1/chat/completions",
        code=401,
        msg="unauthorized",
        hdrs=None,
        fp=None,
    )

    with (
        patch(
            "sentinellayer_growth_engine.conversation_analyzer.urllib.request.urlopen",
            side_effect=error,
        ),
        patch(
            "sentinellayer_growth_engine.conversation_analyzer.time.sleep"
        ) as sleeper,
    ):
        with pytest.raises(ConversationAnalysisError, match="bounded retries"):
                GroqAnalyzer(api_key="bad", max_attempts=4).analyze(
                    subject="Hi",
                    body_text="Hello",
                )
    sleeper.assert_not_called()
