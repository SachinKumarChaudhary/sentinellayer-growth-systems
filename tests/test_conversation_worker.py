import pytest

from sentinellayer_growth_engine.conversation_worker import ConversationWorker
from sentinellayer_growth_engine.imap_inbound import ImapInboundProvider


class Resolver:
    def resolve(self, *, sender_email, thread_key):
        return ("account-1", "42")


class Handler:
    def handle_inbound(self, **kwargs):
        return {"status": "stored"}


def test_conversation_worker_validates_tick():
    with pytest.raises(ValueError):
        ConversationWorker(
            ImapInboundProvider(host="imap.example.com", username="u", password="p"),
            Resolver(),
            Handler(),
            tick_seconds=0,
        )
