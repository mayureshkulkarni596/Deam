from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Literal
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import get_db
from app.dependencies import get_current_user
from app.gate.mock_controller import MockGateController
from app.models import GateRequest
from app.services.audit import record_audit
from app.services.decision_engine import approve_and_open, transition_request

router = APIRouter(prefix="/requests", tags=["requests"])

class DecisionPayload(BaseModel):
    decision: Literal["APPROVE", "REJECT"]

class GateRequestPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    flat_no: str
    mode: str
    visitor_name: str
    purpose: str | None
    status: str
    deny_reason: str | None
    face_mismatch: bool
    decision_source: str
    created_at: object
    expires_at: object | None

def _owned_request(db: Session, request_id: str, user):
    request = db.get(GateRequest, request_id)
    if request is None or user.role != "resident" or request.resident_id != user.id:
        raise HTTPException(status_code=404, detail="Request not found")
    return request

@router.get("", response_model=list[GateRequestPublic])
def list_requests(status: str | None = None, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user.role != "resident":
        raise HTTPException(status_code=403, detail="Resident account required")
    query = select(GateRequest).where(GateRequest.resident_id == user.id)
    if status:
        query = query.where(GateRequest.status == status.upper())
    return db.scalars(query.order_by(GateRequest.created_at.desc()).limit(100)).all()

@router.get("/{request_id}", response_model=GateRequestPublic)
def get_request(request_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return _owned_request(db, request_id, user)

@router.post("/{request_id}/decision")
def decide_request(request_id: str, payload: DecisionPayload, db: Session = Depends(get_db), user=Depends(get_current_user)):
    request = _owned_request(db, request_id, user)
    if payload.decision == "REJECT":
        if not transition_request(db, request_id, expected="PENDING", new_status="REJECTED",
                                  actor_type="USER", actor_id=user.id, source="RESIDENT"):
            db.rollback()
            raise HTTPException(status_code=409, detail="Request is no longer pending")
        db.commit()
        return {"request_id": request_id, "status": "REJECTED"}
    try:
        result = approve_and_open(db, request.id, user.id, MockGateController())
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Request not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="Request is no longer pending") from exc
    record_audit(db, action="RESIDENT_DECISION", entity_type="gate_request", entity_id=request_id,
                 actor_type="USER", actor_id=user.id, details={"decision": payload.decision})
    db.commit()
    return {"request_id": request_id, "status": result.status,
            "message_code": "GATE_OPENING" if result.status == "OPENED" else "HARDWARE_OFFLINE"}
