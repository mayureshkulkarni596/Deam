import hmac
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import GateRequest, User
from app.services.audit import record_audit

router = APIRouter(prefix="/kiosk", tags=["kiosk"])


def require_kiosk_key(x_kiosk_key: str | None = Header(default=None)):
    configured = get_settings().kiosk_api_key
    if not configured or not x_kiosk_key or not hmac.compare_digest(configured, x_kiosk_key):
        raise HTTPException(status_code=401, detail="Invalid or missing kiosk key")
    return True


class GuestRequest(BaseModel):
    flat_no: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=120)
    purpose: str = Field(min_length=1, max_length=300)


@router.post("/guest")
def guest_request(
    payload: GuestRequest,
    request: Request,
    db: Session = Depends(get_db),
    _key=Depends(require_kiosk_key),
):
    resident = db.scalar(
        select(User).where(
            User.flat_number == payload.flat_no, User.role == "resident", User.is_active.is_(True)
        )
    )
    if resident is None:
        raise HTTPException(status_code=404, detail="Flat not found")
    now = datetime.now(UTC)
    gate_request = GateRequest(
        flat_no=payload.flat_no,
        resident_id=resident.id,
        mode="GUEST",
        visitor_name=payload.name.strip(),
        purpose=payload.purpose.strip(),
        status="PENDING",
        decision_source="SYSTEM",
        expires_at=now + timedelta(seconds=get_settings().pending_timeout_seconds),
    )
    db.add(gate_request)
    db.flush()
    record_audit(
        db,
        action="GUEST_REQUEST_CREATED",
        entity_type="gate_request",
        entity_id=gate_request.id,
        actor_type="KIOSK",
        details={"flat_no": payload.flat_no},
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return {
        "request_id": gate_request.id,
        "status": gate_request.status,
        "message_code": "WAITING_FOR_RESIDENT",
        "expires_at": gate_request.expires_at,
    }


@router.get("/requests/{request_id}")
def poll_request(request_id: str, db: Session = Depends(get_db), _key=Depends(require_kiosk_key)):
    gate_request = db.get(GateRequest, request_id)
    if gate_request is None:
        raise HTTPException(status_code=404, detail="Request not found")
    return {
        "request_id": gate_request.id,
        "status": gate_request.status,
        "deny_reason": gate_request.deny_reason,
        "expires_at": gate_request.expires_at,
    }
