from app.gate.mock_controller import MockGateController


def test_mock_gate_records_command_without_hardware():
    gate = MockGateController()
    result = gate.open_gate(request_id="test-1", ttl_ms=8000)
    assert result.success and result.code == "MOCK_OPEN_ACCEPTED"
    assert gate.commands == [{"request_id": "test-1", "ttl_ms": 8000}]


def test_mock_gate_failure_fails_closed():
    gate = MockGateController(fail=True)
    result = gate.open_gate(request_id="test-2", ttl_ms=8000)
    assert not result.success and result.code == "GATE_UNAVAILABLE"
    assert gate.commands == []
