import pytest

from sentinellayer_growth_engine.conversation_inbound import (
    InboundNormalizationError,
    InboundReplyAdapter,
)


def test_normalizes_common_provider_fields():
    msg = InboundReplyAdapter.normalize({
        "provider_message_id": "<m@example.com>",
        "from": "Buyer <buyer@example.com>",
        "subject": "Re: hello",
        "text": "Interested",
        "in_reply_to": "<sent@example.com>",
        "account_id": "account-1",
        "person_id": "person-1",
    })
    assert msg.sender_email == "buyer@example.com"
    assert msg.thread_key == "<sent@example.com>"


def test_missing_thread_key_fails_closed():
    with pytest.raises(InboundNormalizationError):
        InboundReplyAdapter.normalize({
            "provider_message_id": "m",
            "from": "buyer@example.com",
            "account_id": "a",
            "person_id": "p",
        })


def test_adapter_emits_conversation_handoff():
    out = InboundReplyAdapter().process({
        "provider_message_id": "<m@example.com>",
        "from": "Buyer <buyer@example.com>",
        "subject": "Re: hello",
        "text": "Please unsubscribe me",
        "in_reply_to": "<sent@example.com>",
        "account_id": "account-1",
        "person_id": "person-1",
    })
    assert out["classification"] == "unsubscribe"
    assert out["recommended_action"] == "suppress_contact"
