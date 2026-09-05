from sentinellayer_growth_engine.conversation_sales import ConversationSalesBridge


class Store:
    def __init__(self):
        self.items = []

    def create_or_get_open_task(self, handoff):
        self.items.append(handoff)
        return {"sales_task_id": handoff["sales_task_id"], "status": "open"}


def base(classification):
    return {
        "schema_version": "1.0",
        "conversation_id": "11111111-1111-4111-8111-111111111111",
        "reply_id": "22222222-2222-4222-8222-222222222222",
        "account_id": "account-1",
        "person_id": "person-1",
        "classification": classification,
        "conversation_state": "action_selected",
        "recommended_action": "human_follow_up",
        "evidence": [{"signal": "positive reply"}],
        "questions": ["How does this work?"],
        "created_at": "2026-09-05T11:00:00Z",
    }


def test_positive_reply_creates_sales_task():
    store = Store()
    out = ConversationSalesBridge(store).handle(base("interested"), priority="P1")
    assert out["status"] == "sales_task_created"
    assert len(store.items) == 1


def test_question_creates_sales_task():
    store = Store()
    out = ConversationSalesBridge(store).handle(base("question"), priority="P2")
    assert out["status"] == "sales_task_created"


def test_negative_reply_does_not_create_sales_task():
    store = Store()
    out = ConversationSalesBridge(store).handle(base("negative"), priority="P2")
    assert out["status"] == "not_sales_eligible"
    assert store.items == []
