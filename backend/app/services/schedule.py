from datetime import datetime, time

def is_within_schedule(schedule: dict | None, now_local: datetime) -> bool:
    if not schedule:
        return True
    if now_local.weekday() not in schedule.get("days", []):
        return False
    try:
        start = time.fromisoformat(schedule["start"])
        end = time.fromisoformat(schedule["end"])
    except (KeyError, TypeError, ValueError):
        return False
    current = now_local.timetz().replace(tzinfo=None)
    if start <= end:
        return start <= current <= end
    return current >= start or current <= end
