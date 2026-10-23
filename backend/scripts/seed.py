import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.security import hash_password


def create_user(db, email, password, role, flat_number=None):
    email = email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        print(f"Keeping existing account: {email}")
        return
    db.add(User(email=email, password_hash=hash_password(password), role=role, flat_number=flat_number))
    print(f"Created {role} account: {email}")


def main():
    admin_password = os.getenv("SEED_ADMIN_PASSWORD")
    resident_password = os.getenv("SEED_RESIDENT_PASSWORD")
    if not admin_password or not resident_password:
        raise SystemExit("Set SEED_ADMIN_PASSWORD and SEED_RESIDENT_PASSWORD before seeding.")
    if len(admin_password) < 12 or len(resident_password) < 12:
        raise SystemExit("Seed passwords must be at least 12 characters.")
    with SessionLocal() as db:
        create_user(db, os.getenv("SEED_ADMIN_EMAIL", "admin@example.test"), admin_password, "admin")
        create_user(db, os.getenv("SEED_RESIDENT_EMAIL", "resident@example.test"), resident_password, "resident", os.getenv("SEED_RESIDENT_FLAT", "A-101"))
        db.commit()


if __name__ == "__main__":
    main()
