from dataclasses import dataclass

import pytest

from sentinellayer_growth_engine.conversation_analysis_queue import (
    AnalysisJob,
    ConversationAnalysisQueue,
    ConversationAnalysisWorker,
)


def test_queue_requires_dsn_and_worker_id():
    with pytest.raises(ValueError):
        ConversationAnalysisQueue("")
    with pytest.raises(ValueError):
        ConversationAnalysisQueue("postgresql://example", worker_id=" ")


def test_claim_argument_bounds():
    queue = ConversationAnalysisQueue("postgresql://example")
    with pytest.raises(ValueError):
        queue.claim(batch_size=0)
    with pytest.raises(ValueError):
        queue.claim(batch_size=101)
    with pytest.raises(ValueError):
        queue.claim(lease_seconds=9)
    with pytest.raises(ValueError):
        queue.claim(lease_seconds=3601)


@dataclass
class FakeAnalyzer:
    model: str = "openai/gpt-oss-20b"
    calls: int = 0
    received_context: list[str] | None = None

    def analyze(self, *, subject: str, body_text: str, conversation_context: str = "") -> dict[str, object]:
        self.calls += 1
        self.received_context = [conversation_context]
        return {
            "schema_version": "1.0",
            "primary_intent": "objection",
            "secondary_intents": [],
            "objections": [],
            "explicit_opt_out": False,
            "timing_signal": "none",
            "questions": [],
            "evidence": [{"text": body_text, "reason": "test"}],
            "confidence": 0.9,
        }


class FakeQueue:
    def __init__(self, jobs: list[AnalysisJob]) -> None:
        self.jobs = jobs
        self.completed: list[dict[str, object]] = []
        self.failed: list[str] = []

    def claim(self, *, batch_size: int = 10) -> list[AnalysisJob]:
        return self.jobs[:batch_size]

    def complete(self, **kwargs: object) -> None:
        self.completed.append(kwargs)

    def fail(self, *, analysis_id: str, error: str) -> None:
        self.failed.append(analysis_id)


def test_worker_persists_structured_analysis():
    job = AnalysisJob("analysis-1", "reply-1", "Re: hello", "I need a budget review", "thread=1", 1)
    queue = FakeQueue([job])
    analyzer = FakeAnalyzer()

    processed = ConversationAnalysisWorker(queue, analyzer).run_once()

    assert processed == 1
    assert analyzer.calls == 1
    assert queue.failed == []
    assert queue.completed[0]["analysis_id"] == "analysis-1"
    assert queue.completed[0]["provider"] == "groq"
    assert queue.completed[0]["model"] == "openai/gpt-oss-20b"


def test_worker_passes_full_conversation_context_to_analyzer():
    context = (
        "thread_key=thread-42\n"
        "conversation_state=action_selected\n"
        "deterministic_classification=question\n\n"
        "conversation_history:\n"
        "[OUTBOUND] 2026-09-07T10:00:00Z\nSubject: Sentinel Layer\nWe can help with session risk.\n\n"
        "[INBOUND] 2026-09-07T10:05:00Z\nSubject: Re: Sentinel Layer\nHow does this work with our IdP?"
    )
    job = AnalysisJob(
        "analysis-history",
        "reply-history",
        "Re: Sentinel Layer",
        "How does this work with our IdP?",
        context,
        1,
    )
    queue = FakeQueue([job])
    analyzer = FakeAnalyzer()

    ConversationAnalysisWorker(queue, analyzer).run_once()

    assert analyzer.received_context == [context]
    assert "[OUTBOUND]" in analyzer.received_context[0]
    assert "[INBOUND]" in analyzer.received_context[0]
    assert "How does this work with our IdP?" in analyzer.received_context[0]


def test_worker_releases_failed_analysis_back_to_queue():
    job = AnalysisJob("analysis-2", "reply-2", "Re: hello", "text", "thread=2", 1)

    class FailingAnalyzer(FakeAnalyzer):
        def analyze(self, *, subject: str, body_text: str, conversation_context: str = "") -> dict[str, object]:
            raise RuntimeError("provider unavailable")

    queue = FakeQueue([job])
    processed = ConversationAnalysisWorker(queue, FailingAnalyzer()).run_once()

    assert processed == 1
    assert queue.completed == []
    assert queue.failed == ["analysis-2"]
