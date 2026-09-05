import pytest

from sentinellayer_growth_engine.operations_gate import OutboundBlocked, OutboundGate


class Reader:
    def __init__(self, state=None, error=False):
        self.state = state
        self.error = error

    def get_control_state(self):
        if self.error:
            raise RuntimeError("database unavailable")
        return self.state


def test_production_requires_explicit_enabled_state():
    gate = OutboundGate(Reader({
        "environment": "production",
        "outbound_state": "DISABLED",
        "maintenance_mode": True,
    }))
    with pytest.raises(OutboundBlocked):
        gate.assert_send_allowed(environment="production")


def test_production_enabled_allows_gate():
    gate = OutboundGate(Reader({
        "environment": "production",
        "outbound_state": "ENABLED",
        "maintenance_mode": False,
    }))
    gate.assert_send_allowed(environment="production")


def test_state_read_failure_fails_closed():
    gate = OutboundGate(Reader(error=True))
    with pytest.raises(OutboundBlocked):
        gate.assert_send_allowed(environment="production")


def test_safe_stop_blocks_nonproduction():
    gate = OutboundGate(Reader({
        "environment": "staging",
        "outbound_state": "SAFE_STOP",
        "maintenance_mode": True,
    }))
    with pytest.raises(OutboundBlocked):
        gate.assert_send_allowed(environment="staging")
