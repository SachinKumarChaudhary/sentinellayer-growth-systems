from sentinellayer_growth_engine.ids import deterministic_message_id


def test_message_id_is_stable() -> None:
    first = deterministic_message_id("send-123")
    second = deterministic_message_id("send-123")
    assert first == second


def test_different_sends_get_different_ids() -> None:
    assert deterministic_message_id("send-1") != deterministic_message_id("send-2")
