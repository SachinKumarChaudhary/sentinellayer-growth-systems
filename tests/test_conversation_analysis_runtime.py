from sentinellayer_growth_engine.conversation_runtime import ConversationRuntime


class Store:
    def persist_handoff(self, **kwargs):
        return {"reply_id": kwargs["handoff"]["reply_id"], "status": "stored"}

    def cancel_future_sends_for_person(self, *, person_id: int, reason: str) -> None:
        pass

    def add_suppression(self, *, email: str, reason: str) -> None:
        pass


class Queue:
    def __init__(self, *, error: Exception | None = None):
        self.reply_ids = []
        self.error = error

    def enqueue(self, reply_id: str) -> str:
        if self.error is not None:
            raise self.error
        self.reply_ids.append(reply_id)
        return "analysis-1"


def test_runtime_enqueues_persisted_reply_for_semantic_analysis():
    queue = Queue()
    out = ConversationRuntime(Store(), analysis_queue=queue).handle_inbound(
        account_id="account-1",
        person_id="42",
        sender_email="buyer@example.com",
        subject="Re: hello",
        body_text="Can you explain this?",
        provider_message_id="<reply-analysis@example.com>",
        thread_key="<thread-analysis@example.com>",
    )

    assert out["analysis_enqueued"] is True
    assert out["analysis_enqueue_error"] is None
    assert queue.reply_ids == [out["persisted"]["reply_id"]]


def test_analysis_queue_failure_does_not_drop_or_unlock_inbound_processing():
    queue = Queue(error=RuntimeError("queue unavailable"))
    out = ConversationRuntime(Store(), analysis_queue=queue).handle_inbound(
        account_id="account-1",
        person_id="42",
        sender_email="buyer@example.com",
        subject="Re: hello",
        body_text="Please unsubscribe me.",
        provider_message_id="<reply-analysis-stop@example.com>",
        thread_key="<thread-analysis-stop@example.com>",
    )

    assert out["persisted"]["status"] == "stored"
    assert out["analysis_enqueued"] is False
    assert out["analysis_enqueue_error"] == "queue unavailable"
    assert out["stop_sequence"] is True
