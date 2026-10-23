from sqlalchemy.orm import Session
from app.models import AuditLog

def record_audit(db: Session, *, action: str, entity_type: str, entity_id: str | None,
                 actor_type: str = "SYSTEM", actor_id: str | int | None = None,
                 details: dict | None = None, ip: str | None = None) -> AuditLog:
    entry = AuditLog(actor_type=actor_type, actor_id=None if actor_id is None else str(actor_id),
                     action=action, entity_type=entity_type, entity_id=entity_id,
                     details_json=details or {}, ip=ip)
    db.add(entry)
    db.flush()
    return entry
