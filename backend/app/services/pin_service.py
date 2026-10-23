import hashlib
import hmac
from datetime import date
from cryptography.fernet import Fernet, InvalidToken
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

_hasher = PasswordHasher()

def hash_static_pin(pin: str) -> str:
    if len(pin) != 6 or not pin.isascii() or not pin.isdigit():
        raise ValueError("PIN must contain exactly six digits")
    return _hasher.hash(pin)

def verify_static_pin(pin: str, encoded_hash: str) -> bool:
    try:
        return _hasher.verify(encoded_hash, pin)
    except (VerificationError, VerifyMismatchError, ValueError):
        return False

def compute_daily_pin(secret: bytes, visitor_id: int, local_date: date) -> str:
    message = f"{visitor_id}:{local_date.isoformat()}".encode("utf-8")
    digest = hmac.new(secret, message, hashlib.sha256).digest()
    return f"{int.from_bytes(digest[:4], 'big') % 1_000_000:06d}"

def verify_pin(candidate: str, expected: str) -> bool:
    return hmac.compare_digest(candidate.encode("utf-8"), expected.encode("utf-8"))

def encrypt_visitor_secret(secret: bytes, key: str) -> str:
    if not key:
        raise ValueError("DATA_ENCRYPTION_KEY must be configured for DAILY_PIN visitors")
    try:
        return Fernet(key.encode("ascii")).encrypt(secret).decode("ascii")
    except (ValueError, TypeError) as exc:
        raise ValueError("DATA_ENCRYPTION_KEY must be a valid Fernet key") from exc

def decrypt_visitor_secret(token: str, key: str) -> bytes:
    if not key:
        raise ValueError("DATA_ENCRYPTION_KEY is not configured")
    try:
        return Fernet(key.encode("ascii")).decrypt(token.encode("ascii"))
    except (InvalidToken, ValueError, TypeError) as exc:
        raise ValueError("Unable to decrypt visitor PIN secret") from exc
