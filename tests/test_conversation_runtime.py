from datetime import UTC, datetime

from sentinellayer_growth_engine.conversation_runtime import ConversationRuntime


class Store:
    def __init__(self):
        self.persisted = []
        self.cancelled = []
        self.suppressed = []

    def persist_handoff(self, **kwargs):
        self.persisted.append(kwargs)
        return {"reply_id": kwargs["handoff"]["reply_id"], "status": "stored"}

    def cancel_future_sends_for_person(self, *, person_id: int, reason: str) -> None:
        self.cancelled.append((person_id, reason))

    def add_suppression(self, *, email: str, reason: str) -> None:
        self.suppressed.append((email, reason))


def test_unsubscribe_persists_and_stops_future_sends():
    store = Store()
    out = ConversationRuntime(store).handle_inbound(
        account_id="account-1",
        person_id="42",
        sender_email="buyer@example.com",
        subject="Re: hello",
        body_text="Please unsubscribe me",
        provider_message_id="<reply-1@example.com>",
        thread_key="<send-1@example.com>",
        received_at=datetime(2026, 9, 5, 12, tzinfo=UTC),
    )
    assert out["persisted"]["status"] == "stored"
    assert out["stop_sequence"] is True
    assert store.cancelled == [(42, "suppress_contact")]
    assert store.suppressed == [("buyer@example.com", "inbound_unsubscribe")]


def test_interest_can_trigger_sales_bridge():
    class Bridge:
        def __init__(self):
            self.calls = []

        def bridge(self, conversation, *, priority):
            self.calls.append((conversation, priority))
            return {"status": "task_created"}

    bridge = Bridge()
    store = Store()
    out = ConversationRuntime(store, sales_bridge=bridge).handle_inbound(
        account_id="account-1",
        person_id="42",
        sender_email="buyer@example.com",
        subject="Re: hello",
        body_text="Interested, let's talk.",
        provider_message_id="<reply-2@example.com>",
        thread_key="<send-2@example.com>",
        received_at=datetime(2026, 9, 5, 12, tzinfo=UTC),
    )
    assert out["sales"]["status"] == "task_created"
    assert len(bridge.calls) == 1


def test_non_numeric_person_id_fails_closed_without_cancel():
    store = Store()
    out = ConversationRuntime(store).handle_inbound(
        account_id="account-1",
        person_id="person-1",
        sender_email="buyer@example.com",
        subject="Re: hello",
        body_text="Not interested",
        provider_message_id="<reply-3@example.com>",
        thread_key="<send-3@example.com>",
    )
    assert out["stop_sequence"] is True
    assert store.cancelled == []
