import pytest

from sentinellayer_growth_engine.conversation_sales import ConversationSalesBridge


class Store:
    def __init__(self):
        self.handoff = None

    def upsert_open_task(self, handoff):
        self.handoff = handoff
        return handoff


def conversation(classification):
    return {
        "schema_version": "1.0",
        "conversation_id": "11111111-1111-4111-8111-111111111111",
        "reply_id": "22222222-2222-4222-8222-222222222222",
        "account_id": "account-1",
        "person_id": "person-1",
        "classification": classification,
        "conversation_state": "action_selected",
        "recommended_action": (
            "human_follow_up" if classification in {"interested", "question"} else "human_review"
        ),
        "created_at": "2026-09-05T12:00:00Z",
    }


def test_interested_creates_sales_task():
    store = Store()
    out = ConversationSalesBridge(store).bridge(conversation("interested"), priority="P1")
    assert out["trigger_type"] == "interested"
    assert out["priority"] == "P1"
    assert store.handoff is not None


def test_question_creates_sales_task():
    store = Store()
    out = ConversationSalesBridge(store).bridge(conversation("question"), priority="P2")
    assert out["trigger_type"] == "question"


def test_negative_does_not_create_sales_task():
    with pytest.raises(Exception):
        ConversationSalesBridge(Store()).bridge(conversation("negative"), priority="P2")
