from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import GateRequest
from app.services.decision_engine import transition_request

def expire_pending_requests(db: Session, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    ids = db.scalars(select(GateRequest.id).where(
        GateRequest.status == "PENDING", GateRequest.expires_at.is_not(None),
        GateRequest.expires_at <= now
    )).all()
    count = 0
    for request_id in ids:
        if transition_request(db, request_id, expected="PENDING", new_status="EXPIRED",
                              actor_type="SYSTEM", actor_id=None, source="TIMEOUT", reason="PENDING_TIMEOUT"):
            count += 1
    db.commit()
    return count

def cleanup_old_snapshots(storage_dir: str, retention_days: int = 30) -> int:
    root = Path(storage_dir).resolve()
    if not root.exists():
        return 0
    cutoff = datetime.now(timezone.utc).timestamp() - max(1, retention_days) * 86400
    deleted = 0
    for path in root.glob("*.jpg"):
        try:
            if path.is_file() and path.resolve().parent == root and path.stat().st_mtime < cutoff:
                path.unlink()
                deleted += 1
        except OSError:
            continue
    return deleted
