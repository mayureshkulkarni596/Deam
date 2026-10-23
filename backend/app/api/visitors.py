import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.dependencies import get_current_user
from app.models import FaceEmbedding, Visitor
from app.schemas import VisitorCreate, VisitorPublic
from app.services.audit import record_audit
from app.services.face_service import FaceService
from app.services.pin_service import (
    compute_daily_pin,
    decrypt_visitor_secret,
    encrypt_visitor_secret,
    hash_static_pin,
)

router = APIRouter(prefix="/visitors", tags=["visitors"])
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png"}
MAX_IMAGE_BYTES = 3 * 1024 * 1024


def _require_resident(user):
    if user.role != "resident" or not user.flat_number:
        raise HTTPException(status_code=403, detail="Resident account required")


def _owned_visitor(db: Session, visitor_id: int, user):
    visitor = db.scalar(
        select(Visitor).where(Visitor.id == visitor_id, Visitor.resident_id == user.id)
    )
    if visitor is None:
        raise HTTPException(status_code=404, detail="Visitor not found")
    return visitor


@router.get("", response_model=list[VisitorPublic])
def list_visitors(db: Session = Depends(get_db), user=Depends(get_current_user)):
    _require_resident(user)
    return db.scalars(
        select(Visitor).where(Visitor.resident_id == user.id).order_by(Visitor.id.desc())
    ).all()


@router.post("", response_model=VisitorPublic, status_code=status.HTTP_201_CREATED)
def create_visitor(
    payload: VisitorCreate, db: Session = Depends(get_db), user=Depends(get_current_user)
):
    _require_resident(user)
    pin_hash, secret_enc = None, None
    if payload.credential_mode == "STATIC_PIN":
        pin_hash = hash_static_pin(payload.pin or "")
    else:
        settings = get_settings()
        try:
            secret_enc = encrypt_visitor_secret(
                secrets.token_bytes(32), settings.data_encryption_key
            )
        except ValueError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    visitor = Visitor(
        resident_id=user.id,
        name=payload.name.strip(),
        phone=payload.phone.strip(),
        category=payload.category,
        credential_mode=payload.credential_mode,
        pin_hash=pin_hash,
        secret_enc=secret_enc,
        auto_open=payload.auto_open,
        schedule_json=payload.schedule,
        outside_schedule_action=payload.outside_schedule_action,
        valid_from=payload.valid_from,
        valid_until=payload.valid_until,
    )
    db.add(visitor)
    db.flush()
    record_audit(
        db,
        action="VISITOR_CREATED",
        entity_type="visitor",
        entity_id=str(visitor.id),
        actor_type="USER",
        actor_id=user.id,
        details={"category": visitor.category},
    )
    db.commit()
    db.refresh(visitor)
    return visitor


class VisitorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, min_length=3, max_length=32)
    category: str | None = None
    auto_open: bool | None = None
    schedule_json: dict | None = None
    outside_schedule_action: str | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    pin: str | None = Field(default=None, min_length=6, max_length=6, pattern=r"^\d{6}$")


@router.patch("/{visitor_id}", response_model=VisitorPublic)
def update_visitor(
    visitor_id: int,
    payload: VisitorUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _require_resident(user)
    visitor = _owned_visitor(db, visitor_id, user)
    changes = payload.model_dump(exclude_unset=True)
    if "pin" in changes:
        pin = changes.pop("pin")
        if visitor.credential_mode != "STATIC_PIN" or pin is None:
            raise HTTPException(
                status_code=422, detail="PIN can only be changed for STATIC_PIN visitors"
            )
        visitor.pin_hash = hash_static_pin(pin)
    if "category" in changes and changes["category"] not in {
        "MAID",
        "DRIVER",
        "RELATIVE",
        "WORKER",
        "OTHER",
    }:
        raise HTTPException(status_code=422, detail="Invalid visitor category")
    if "outside_schedule_action" in changes and changes["outside_schedule_action"] not in {
        "ASK",
        "DENY",
    }:
        raise HTTPException(status_code=422, detail="Invalid outside_schedule_action")
    for field, value in changes.items():
        setattr(visitor, field, value)
    record_audit(
        db,
        action="VISITOR_UPDATED",
        entity_type="visitor",
        entity_id=str(visitor.id),
        actor_type="USER",
        actor_id=user.id,
    )
    db.commit()
    db.refresh(visitor)
    return visitor


@router.delete("/{visitor_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_visitor(visitor_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    _require_resident(user)
    visitor = _owned_visitor(db, visitor_id, user)
    visitor.status = "REVOKED"
    visitor.auto_open = False
    db.execute(delete(FaceEmbedding).where(FaceEmbedding.visitor_id == visitor.id))
    record_audit(
        db,
        action="VISITOR_REVOKED",
        entity_type="visitor",
        entity_id=str(visitor.id),
        actor_type="USER",
        actor_id=user.id,
    )
    db.commit()


@router.get("/{visitor_id}/today-pin")
def today_pin(visitor_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    _require_resident(user)
    visitor = _owned_visitor(db, visitor_id, user)
    if visitor.credential_mode != "DAILY_PIN" or not visitor.secret_enc:
        raise HTTPException(status_code=409, detail="Visitor does not use DAILY_PIN")
    settings = get_settings()
    try:
        secret = decrypt_visitor_secret(visitor.secret_enc, settings.data_encryption_key)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    from zoneinfo import ZoneInfo

    local_date = datetime.now(ZoneInfo(settings.app_timezone)).date()
    return {
        "visitor_id": visitor.id,
        "pin": compute_daily_pin(secret, visitor.id, local_date),
        "valid_date": local_date.isoformat(),
    }


@router.post("/{visitor_id}/faces")
async def enroll_faces(
    visitor_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    _require_resident(user)
    visitor = _owned_visitor(db, visitor_id, user)
    if not 3 <= len(files) <= 5:
        raise HTTPException(status_code=422, detail="Upload 3 to 5 face images")
    settings = get_settings()
    face_service = FaceService(
        settings.face_model_dir, settings.face_min_width_px, settings.face_min_sharpness
    )
    if not face_service.available:
        raise HTTPException(status_code=503, detail="Face models are not installed")
    results, good = [], []
    for upload in files:
        if upload.content_type not in ALLOWED_IMAGE_TYPES:
            results.append(
                {"filename": upload.filename, "ok": False, "code": "UNSUPPORTED_IMAGE_TYPE"}
            )
            continue
        data = await upload.read(MAX_IMAGE_BYTES + 1)
        if len(data) > MAX_IMAGE_BYTES:
            results.append({"filename": upload.filename, "ok": False, "code": "IMAGE_TOO_LARGE"})
            continue
        checked = face_service.inspect(data)
        results.append({"filename": upload.filename, "ok": checked.ok, "code": checked.code})
        if checked.ok and checked.embedding is not None:
            good.append((checked.embedding.tobytes(), checked.quality_score))
    if len(good) < 3:
        raise HTTPException(
            status_code=422,
            detail={"message": "At least 3 good face images are required", "results": results},
        )
    db.execute(delete(FaceEmbedding).where(FaceEmbedding.visitor_id == visitor.id))
    for embedding, quality in good:
        db.add(
            FaceEmbedding(
                visitor_id=visitor.id,
                embedding=embedding,
                model_version="opencv-sface-2021dec",
                quality_score=quality,
            )
        )
    record_audit(
        db,
        action="VISITOR_FACES_ENROLLED",
        entity_type="visitor",
        entity_id=str(visitor.id),
        actor_type="USER",
        actor_id=user.id,
        details={"good_images": len(good)},
    )
    db.commit()
    return {"visitor_id": visitor.id, "enrolled": len(good), "results": results}
