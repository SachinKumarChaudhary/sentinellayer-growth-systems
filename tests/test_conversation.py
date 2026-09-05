from datetime import UTC, datetime
from uuid import UUID

import pytest

from sentinellayer_growth_engine.conversation import ConversationProcessor, classify_reply
from sentinellayer_growth_engine.contracts import ContractValidationError


def test_unsubscribe_is_deterministic():
    classification, reason = classify_reply("Re: hello", "Please unsubscribe me.")
    assert classification == "unsubscribe"
    assert reason == "explicit_unsubscribe"


def test_interest_beats_question():
    classification, _ = classify_reply("Re: question", "Interested — can you send me more?")
    assert classification == "interested"


def test_question_is_classified():
    classification, _ = classify_reply("Re: Sentinel", "Can you explain how this works?")
    assert classification == "question"


def test_processor_emits_valid_handoff():
    result = ConversationProcessor().process(
        account_id="account-1",
        person_id="person-1",
        sender_email="buyer@example.com",
        subject="Re: hello",
        body_text="Interested, let's talk next week.",
        provider_message_id="<msg-123@example.com>",
        thread_key="thread-123",
        source_send_id="00000000-0000-4000-8000-000000000001",
        received_at=datetime(2026, 9, 5, 8, 0, tzinfo=UTC),
    )
    assert result["classification"] == "interested"
    assert result["conversation_state"] == "action_selected"
    assert UUID(result["conversation_id"])
    assert result["recommended_action"] == "human_follow_up"


def test_invalid_source_send_id_rejected():
    with pytest.raises(ContractValidationError):
        ConversationProcessor().process(
            account_id="a",
            person_id="p",
            sender_email="x@example.com",
            subject="Hi",
            body_text="Hello",
            provider_message_id="m",
            thread_key="t",
            source_send_id="not-a-uuid",
        )
