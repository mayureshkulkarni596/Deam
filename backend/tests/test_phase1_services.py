from datetime import date, datetime
from types import SimpleNamespace
from app.services.pin_service import compute_daily_pin, hash_static_pin, verify_static_pin, verify_pin
from app.services.schedule import is_within_schedule
from app.services.decision_engine import evaluate_visit

def test_daily_pin_is_deterministic_and_changes_by_date():
    secret = b"test-secret"
    assert compute_daily_pin(secret, 7, date(2026, 10, 23)) == compute_daily_pin(secret, 7, date(2026, 10, 23))
    assert compute_daily_pin(secret, 7, date(2026, 10, 23)) != compute_daily_pin(secret, 7, date(2026, 10, 24))

def test_static_pin_hash_and_constant_time_compare():
    hashed = hash_static_pin("123456")
    assert verify_static_pin("123456", hashed)
    assert not verify_static_pin("000000", hashed)
    assert verify_pin("123456", "123456")
    assert not verify_pin("123456", "123457")

def test_schedule_regular_and_overnight():
    schedule = {"days": [4], "start": "22:00", "end": "02:00"}
    assert is_within_schedule(schedule, datetime.fromisoformat("2026-10-23T23:30:00"))
    assert not is_within_schedule(schedule, datetime.fromisoformat("2026-10-24T12:00:00"))

def test_decision_fails_closed_for_bad_pin_or_face():
    settings = SimpleNamespace(face_match_threshold=0.363, app_timezone="Asia/Kolkata")
    visitor = SimpleNamespace(status="ACTIVE", valid_from=None, valid_until=None,
                              outside_schedule_action="ASK", schedule_json=None, auto_open=True)
    assert evaluate_visit(visitor, False, 0.9, datetime.fromisoformat("2026-10-23T10:00:00+00:00"), settings).reason == "PIN_INVALID"
    assert evaluate_visit(visitor, True, 0.1, datetime.fromisoformat("2026-10-23T10:00:00+00:00"), settings).reason == "FACE_MISMATCH"
