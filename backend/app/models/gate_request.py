import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Float, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

class GateRequest(Base):
    __tablename__ = "gate_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    flat_no: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    resident_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    visitor_id: Mapped[int | None] = mapped_column(ForeignKey("visitors.id", ondelete="SET NULL"), nullable=True, index=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    visitor_name: Mapped[str] = mapped_column(String(120), nullable=False)
    purpose: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    deny_reason: Mapped[str | None] = mapped_column(String(50))
    pin_valid: Mapped[bool | None] = mapped_column(Boolean)
    face_score: Mapped[float | None] = mapped_column(Float)
    face_mismatch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    snapshot_path: Mapped[str | None] = mapped_column(String(500))
    decision_source: Mapped[str] = mapped_column(String(20), nullable=False, default="SYSTEM")
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    kiosk_id: Mapped[int | None] = mapped_column(ForeignKey("kiosks.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (Index("ix_gate_requests_status_created_at", "status", "created_at"),)
