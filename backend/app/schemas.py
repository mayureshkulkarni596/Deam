from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    role: str
    flat_number: str | None
    is_active: bool

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserPublic

class VisitorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=3, max_length=32)
    category: Literal["MAID", "DRIVER", "RELATIVE", "WORKER", "OTHER"]
    credential_mode: Literal["STATIC_PIN", "DAILY_PIN"]
    pin: str | None = Field(default=None, min_length=6, max_length=6, pattern=r"^\d{6}$")
    auto_open: bool = False
    schedule: dict | None = None
    outside_schedule_action: Literal["ASK", "DENY"] = "ASK"
    valid_from: datetime | None = None
    valid_until: datetime | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.valid_from and self.valid_until and self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be after valid_from")
        if self.credential_mode == "STATIC_PIN" and self.pin is None:
            raise ValueError("PIN is required for STATIC_PIN")
        if self.credential_mode == "DAILY_PIN" and self.pin is not None:
            raise ValueError("PIN must be omitted for DAILY_PIN")
        return self

class VisitorPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    resident_id: int
    name: str
    phone: str
    category: str
    credential_mode: str
    auto_open: bool
    schedule_json: dict | None
    outside_schedule_action: str
    valid_from: datetime | None
    valid_until: datetime | None
    status: str
    created_at: datetime
