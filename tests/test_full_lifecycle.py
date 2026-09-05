from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from sentinellayer_growth_engine.conversation_runtime import ConversationRuntime
from sentinellayer_growth_engine.conversation_sales import ConversationSalesBridge
from sentinellayer_growth_engine.engine import SendEngine
from sentinellayer_growth_engine.mail_handoff import CampaignMailHandoff
from sentinellayer_growth_engine.providers import MockMailProvider
from sentinellayer_growth_engine.tracking import build_tracking_event



T = {
    "schema_version": "1.0",
    "enrollment_id": "55555555-5555-4555-8555-555555555555",
    "campaign_id": "11111111-1111-4111-8111-111111111111",
    "person_id": "person-1",
    "account_id": "account-1",
    "sequence_step_id": "22222222-2222-4222-8222-222222222222",
    "strategy_version_id": "66666666-6666-4666-8666-666666666666",
    "offer_version_id": "77777777-7777-4777-8777-777777777777",
    "message_version_id": "88888888-8888-4888-8888-888888888888",
    "cta_version_id": "99999999-9999-4999-8999-999999999999",
    "sequence_version_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    "recipient_email": "buyer@example.com",
    "subject": "Sentinel Layer",
    "body_text": "A deterministic pilot message.",
    "headers": {},
    "rendered_at": "2026-09-05T12:00:00+00:00",
}


class SendRepo:
    def __init__(self) -> None:
        self.sends = [{
            "send_id": "44444444-4444-4444-8444-444444444444",
            "sender": "pilot@example.com",
            "recipient": "buyer@example.com",
            "subject": T["subject"],
            "body_text": T["body_text"],
            "message_id": "<send-1@example.com>",
            "attempt_count": 1,
        }]
        self.marked_sent = []

    def claim_due(self, **_kwargs):
        return list(self.sends)

    def mark_sent(self, **kwargs):
        self.marked_sent.append(kwargs)

    def mark_ambiguous(self, **_kwargs):
        raise AssertionError("unexpected ambiguous provider state")

    def resolve_uncertain(self, **_kwargs):
        raise AssertionError("unexpected uncertain reconciliation")

    def mark_failed(self, **kwargs):
        raise AssertionError(f"unexpected provider failure: {kwargs}")


class ConversationStore:
    def __init__(self) -> None:
        self.persisted = []
        self.cancelled = []
        self.suppressed = []

    def persist_handoff(self, **kwargs):
        self.persisted.append(kwargs)
        return {"reply_id": kwargs["handoff"]["reply_id"], "status": "stored"}

    def cancel_future_sends_for_person(self, **kwargs):
        self.cancelled.append(kwargs)

    def add_suppression(self, **kwargs):
        self.suppressed.append(kwargs)


class SalesStore:
    def __init__(self) -> None:
        self.tasks = []

    def upsert_open_task(self, handoff):
        self.tasks.append(handoff)
        return {"sales_task_id": handoff["sales_task_id"], "status": "task_created"}


@pytest.mark.asyncio
async def test_campaign_mail_tracking_conversation_sales_lifecycle() -> None:
    send_request = CampaignMailHandoff().build_send_request(
        treatment=T,
        mailbox_id="33333333-3333-4333-8333-333333333333",
        scheduled_at=datetime(2026, 9, 5, 12, tzinfo=UTC),
        send_id="44444444-4444-4444-8444-444444444444",
    )
    assert send_request["treatment"] == T

    repo = SendRepo()
    provider = MockMailProvider()
    processed = await SendEngine(repo, provider).process_due(
        batch_size=1,
        worker_id="synthetic-e2e",
        now=datetime(2026, 9, 5, 12, tzinfo=UTC),
    )
    assert processed == 1
    assert repo.marked_sent[0]["provider_message_id"] == "<send-1@example.com>"
    assert provider.sent[0].subject == T["subject"]
    assert provider.sent[0].body_text == T["body_text"]

    tracking = build_tracking_event(
        event_type="link_clicked",
        source_system="tracking",
        environment="test",
        correlation_id="corr-e2e-1",
        account_id="account-1",
        person_id="person-1",
        campaign_id=T["campaign_id"],
        send_id=send_request["send_id"],
        occurred_at=datetime(2026, 9, 5, 12, 1, tzinfo=UTC),
        payload={"link_type": "cta"},
    )
    assert tracking.correlation_id == "corr-e2e-1"
    assert tracking.send_id == send_request["send_id"]

    sales_store = SalesStore()
    conversation_store = ConversationStore()
    runtime = ConversationRuntime(
        conversation_store,
        sales_bridge=ConversationSalesBridge(sales_store),
    )
    outcome = runtime.handle_inbound(
        account_id="account-1",
        person_id="person-1",
        sender_email="buyer@example.com",
        subject="Re: Sentinel Layer",
        body_text="Interested, please send details.",
        provider_message_id="<reply-1@example.com>",
        thread_key="<send-1@example.com>",
        source_send_id=send_request["send_id"],
        received_at=datetime(2026, 9, 5, 12, 2, tzinfo=UTC),
    )
    assert outcome["persisted"]["status"] == "stored"
    assert outcome["sales"]["status"] == "task_created"
    assert len(sales_store.tasks) == 1
    assert conversation_store.cancelled == []
    assert UUID(sales_store.tasks[0]["sales_task_id"])


def test_unsubscribe_path_is_terminal_for_future_outbound() -> None:
    store = ConversationStore()
    outcome = ConversationRuntime(store).handle_inbound(
        account_id="account-1",
        person_id="1",
        sender_email="buyer@example.com",
        subject="Re: Sentinel Layer",
        body_text="Please unsubscribe me.",
        provider_message_id="<reply-unsub@example.com>",
        thread_key="<send-1@example.com>",
        received_at=datetime(2026, 9, 5, 12, 2, tzinfo=UTC),
    )
    assert outcome["stop_sequence"] is True
    assert store.suppressed == [
        {"email": "buyer@example.com", "reason": "inbound_unsubscribe"}
    ]
    assert store.cancelled == [
        {"person_id": 1, "reason": "suppress_contact"}
    ]
