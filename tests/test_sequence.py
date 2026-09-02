from datetime import datetime, timezone

import pytest

from sentinellayer_growth_engine.sequence import EnrollmentState, SequenceOrchestrationError, SequenceOrchestrator

def step(no, version="q1", delay=0, active=True):
    return {"id": f"st{no}", "sequence_version_id": version, "step_no": no, "delay_days": delay, "active": active}

def enrollment(**overrides):
    data = {"enrollment_id": "e1", "sequence_version_id": "q1", "current_step_no": 0, "status": "active", "next_action_at": None}
    data.update(overrides)
    return EnrollmentState(**data)

def test_selects_first_step():
    now = datetime(2026, 9, 2, tzinfo=timezone.utc)
    action = SequenceOrchestrator().next_action(enrollment=enrollment(), sequence_steps=[step(1), step(2, delay=2)], now=now, max_steps=5)
    assert action.step["step_no"] == 1
    assert action.scheduled_at == now

def test_applies_step_delay():
    now = datetime(2026, 9, 2, tzinfo=timezone.utc)
    action = SequenceOrchestrator().next_action(enrollment=enrollment(current_step_no=1), sequence_steps=[step(1), step(2, delay=3)], now=now, max_steps=5)
    assert action.scheduled_at == datetime(2026, 9, 5, tzinfo=timezone.utc)

def test_waits_until_next_action():
    now = datetime(2026, 9, 2, tzinfo=timezone.utc)
    action = SequenceOrchestrator().next_action(enrollment=enrollment(next_action_at=datetime(2026, 9, 3, tzinfo=timezone.utc)), sequence_steps=[step(1)], now=now, max_steps=5)
    assert action is None

def test_terminal_enrollment_does_not_advance():
    now = datetime(2026, 9, 2, tzinfo=timezone.utc)
    action = SequenceOrchestrator().next_action(enrollment=enrollment(status="replied"), sequence_steps=[step(1)], now=now, max_steps=5)
    assert action is None

def test_wrong_sequence_version_is_rejected():
    now = datetime(2026, 9, 2, tzinfo=timezone.utc)
    with pytest.raises(SequenceOrchestrationError):
        SequenceOrchestrator().next_action(enrollment=enrollment(), sequence_steps=[step(1, version="q2")], now=now, max_steps=5)

def test_missing_step_is_rejected():
    now = datetime(2026, 9, 2, tzinfo=timezone.utc)
    with pytest.raises(SequenceOrchestrationError):
        SequenceOrchestrator().next_action(enrollment=enrollment(), sequence_steps=[step(2)], now=now, max_steps=5)
