from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import or_, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.gate.base import GateController
from app.models import GateRequest, Visitor
from app.services.audit import record_audit
from app.services.schedule import is_within_schedule


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str | None = None


def evaluate_visit(
    visitor: Visitor | None,
    pin_ok: bool,
    face_score: float | None,
    now: datetime,
    settings,
    *,
    face_quality_ok: bool = True,
) -> Decision:
    if not pin_ok:
        return Decision("DENY", "PIN_INVALID")
    if visitor is None or visitor.status != "ACTIVE":
        return Decision("DENY", "VISITOR_REVOKED")
    # SQLite may return naive datetimes for timezone-aware columns. Normalize
    # both sides to UTC before comparing so boundary checks never raise TypeError.
    now_utc = now.replace(tzinfo=UTC) if now.tzinfo is None else now.astimezone(UTC)

    def as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    if visitor.valid_from and now_utc < as_utc(visitor.valid_from):
        return Decision("DENY", "VISITOR_NOT_YET_VALID")
    if visitor.valid_until and now_utc > as_utc(visitor.valid_until):
        return Decision("DENY", "VISITOR_EXPIRED")
    if not face_quality_ok or face_score is None or face_score < settings.face_match_threshold:
        return Decision("DENY", "FACE_MISMATCH")
    local_now = now.astimezone(ZoneInfo(settings.app_timezone))
    if not is_within_schedule(visitor.schedule_json, local_now):
        return Decision(
            "DENY" if visitor.outside_schedule_action == "DENY" else "NEEDS_APPROVAL",
            "OUTSIDE_SCHEDULE",
        )
    return Decision("AUTO_OPEN") if visitor.auto_open else Decision("NEEDS_APPROVAL")


def transition_request(
    db: Session,
    request_id: str,
    *,
    expected: str,
    new_status: str,
    actor_type: str,
    actor_id: str | int | None,
    source: str,
    reason: str | None = None,
) -> bool:
    allowed = {
        "PENDING": {"APPROVED", "REJECTED", "EXPIRED", "DENIED"},
        "APPROVED": {"OPENING"},
        "OPENING": {"OPENED", "FAILED"},
    }
    if new_status not in allowed.get(expected, set()):
        return False
    now = datetime.now(UTC)
    conditions = [GateRequest.id == request_id, GateRequest.status == expected]
    if expected == "PENDING" and new_status == "APPROVED":
        # Approval must fail closed if the request expired, even if the periodic
        # expiry worker has not processed it yet.
        conditions.append(or_(GateRequest.expires_at.is_(None), GateRequest.expires_at > now))
    result = db.execute(
        update(GateRequest)
        .where(*conditions)
        .values(status=new_status, decision_source=source, deny_reason=reason, decided_at=now)
    )
    if result.rowcount != 1:
        return False
    record_audit(
        db,
        action=f"REQUEST_{new_status}",
        entity_type="gate_request",
        entity_id=request_id,
        actor_type=actor_type,
        actor_id=actor_id,
        details={"from": expected, "to": new_status, "reason": reason},
    )
    return True


def approve_and_open(
    db: Session, request_id: str, actor_id: int, gate: GateController
) -> GateRequest:
    request = db.get(GateRequest, request_id)
    if request is None:
        raise LookupError("REQUEST_NOT_FOUND")
    if not transition_request(
        db,
        request_id,
        expected="PENDING",
        new_status="APPROVED",
        actor_type="USER",
        actor_id=actor_id,
        source="RESIDENT",
    ):
        db.rollback()
        raise ValueError("REQUEST_NOT_PENDING")
    db.commit()
    if not transition_request(
        db,
        request_id,
        expected="APPROVED",
        new_status="OPENING",
        actor_type="USER",
        actor_id=actor_id,
        source="RESIDENT",
    ):
        db.rollback()
        raise ValueError("REQUEST_NOT_APPROVED")
    db.commit()
    try:
        result = gate.open_gate(request_id=request_id, ttl_ms=get_settings().gate_open_ttl_ms)
    except Exception:
        result = None
    final = "OPENED" if result and result.success else "FAILED"
    reason = None if final == "OPENED" else (result.code if result else "GATE_COMMAND_ERROR")
    if not transition_request(
        db,
        request_id,
        expected="OPENING",
        new_status=final,
        actor_type="SYSTEM",
        actor_id=None,
        source="SYSTEM",
        reason=reason,
    ):
        db.rollback()
        raise RuntimeError("REQUEST_FINALIZATION_FAILED")
    db.commit()
    return db.get(GateRequest, request_id)
