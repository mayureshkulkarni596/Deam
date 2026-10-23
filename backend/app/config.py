from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Deam Smart Society Gate"
    app_env: str = "dev"
    app_timezone: str = "Asia/Kolkata"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./gate.db"
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    log_level: str = "INFO"
    gate_mode: str = "mock"
    serial_port: str = "COM3"
    serial_baud: int = 115200
    gate_open_ttl_ms: int = 8000
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
