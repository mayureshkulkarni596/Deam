from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Deam Smart Society Gate"
    app_env: str = "dev"
    app_timezone: str = "Asia/Kolkata"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./gate.db"
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    log_level: str = "INFO"
    gate_mode: str = "mock"
    serial_port: str = "COM3"
    serial_baud: int = 115200
    gate_open_ttl_ms: int = 8000
    data_encryption_key: str = ""
    kiosk_api_key: str = ""
    face_model_dir: str = "models"
    face_match_threshold: float = 0.363
    face_min_width_px: int = 80
    face_min_sharpness: float = 60.0
    pending_timeout_seconds: int = 120
    allow_ask_resident_on_face_fail: bool = True
    snapshot_retention_days: int = 30
    mock_fail_rate: float = 0.0
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.app_env.strip().lower() == "production":
            if not self.jwt_secret or self.jwt_secret == "dev-only-change-me":
                raise ValueError("JWT_SECRET must be set to a unique production secret")
            if not self.data_encryption_key:
                raise ValueError("DATA_ENCRYPTION_KEY is required in production")
            if not self.kiosk_api_key:
                raise ValueError("KIOSK_API_KEY is required in production")
        return self

    @field_validator("gate_mode")
    @classmethod
    def valid_gate_mode(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"mock", "serial"}:
            raise ValueError("GATE_MODE must be mock or serial")
        return value

    @field_validator("jwt_expire_minutes")
    @classmethod
    def valid_jwt_expiry(cls, value: int) -> int:
        if not 1 <= value <= 1440:
            raise ValueError("JWT_EXPIRE_MINUTES must be 1..1440")
        return value

    @field_validator("gate_open_ttl_ms")
    @classmethod
    def valid_gate_ttl(cls, value: int) -> int:
        if not 1000 <= value <= 15000:
            raise ValueError("GATE_OPEN_TTL_MS must be 1000..15000")
        return value

    @field_validator("face_match_threshold")
    @classmethod
    def valid_face_threshold(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("FACE_MATCH_THRESHOLD must be between 0 and 1")
        return value

    @field_validator("mock_fail_rate")
    @classmethod
    def valid_mock_fail_rate(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("MOCK_FAIL_RATE must be between 0 and 1")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
