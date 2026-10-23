from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GateResult:
    success: bool
    code: str
    message: str


class GateController(Protocol):
    def open_gate(self, *, request_id: str, ttl_ms: int) -> GateResult:
        """Request a bounded opening; implementations must fail closed."""
        ...
