from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LoginAttempt


def is_rate_limited(
    db: Session,
    key: str,
    *,
    max_failures: int = 5,
    window_seconds: int = 600,
    lockout_seconds: int = 600,
) -> bool:
    now = datetime.now(UTC)
    rows = db.scalars(
        select(LoginAttempt)
        .where(
            LoginAttempt.key == key,
            LoginAttempt.success.is_(False),
            LoginAttempt.created_at
            >= now - timedelta(seconds=max(window_seconds, lockout_seconds)),
        )
        .order_by(LoginAttempt.created_at.desc())
    ).all()
    failures = []
    for row in rows:
        stamp = row.created_at
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=UTC)
        if stamp >= now - timedelta(seconds=window_seconds):
            failures.append(stamp)
    return len(failures) >= max_failures and failures[0] >= now - timedelta(seconds=lockout_seconds)


def record_attempt(db: Session, key: str, success: bool) -> None:
    db.add(LoginAttempt(key=key, success=success))
    db.flush()
