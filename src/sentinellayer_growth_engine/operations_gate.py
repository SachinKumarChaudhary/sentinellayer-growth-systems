from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class OperationsStateReader(Protocol):
    def get_control_state(self) -> dict[str, object]: ...


class OutboundBlocked(RuntimeError):
    """Raised whenever Operations does not explicitly permit production mail."""


@dataclass(frozen=True)
class OutboundGate:
    reader: OperationsStateReader

    def assert_send_allowed(self, *, environment: str) -> None:
        try:
            state = self.reader.get_control_state()
        except Exception as exc:
            raise OutboundBlocked("operations control state unavailable; outbound blocked") from exc

        if environment != "production":
            if state.get("outbound_state") == "SAFE_STOP":
                raise OutboundBlocked("operations safe-stop active")
            return

        if state.get("environment") != "production":
            raise OutboundBlocked("operations environment mismatch")

        if state.get("outbound_state") != "ENABLED":
            raise OutboundBlocked("production outbound is not enabled")

        if state.get("maintenance_mode") is not False:
            raise OutboundBlocked("operations maintenance mode is active")
