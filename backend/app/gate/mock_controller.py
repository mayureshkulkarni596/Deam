import logging

from app.gate.base import GateResult

logger = logging.getLogger(__name__)


class MockGateController:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.commands: list[dict[str, object]] = []

    def open_gate(self, *, request_id: str, ttl_ms: int) -> GateResult:
        if self.fail:
            logger.warning("Mock gate command failed request_id=%s", request_id)
            return GateResult(False, "GATE_UNAVAILABLE", "Mock gate is configured to fail")
        self.commands.append({"request_id": request_id, "ttl_ms": ttl_ms})
        logger.info("Mock command accepted request_id=%s ttl_ms=%s", request_id, ttl_ms)
        return GateResult(True, "MOCK_OPEN_ACCEPTED", "No physical gate moved")
