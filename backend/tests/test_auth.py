from app.db import get_db
from app.models import User
from app.security import hash_password


def test_login_succeeds(client):
    session_generator = client.app.dependency_overrides[get_db]()
    db = next(session_generator)
    db.add(
        User(
            email="resident@example.com",
            password_hash=hash_password("long-test-password"),
            role="resident",
            flat_number="A-101",
            is_active=True,
        )
    )
    db.commit()
    db.close()
    session_generator.close()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "resident@example.com",
            "password": "long-test-password",
        },
    )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "resident"
    assert response.json()["access_token"]


def test_login_rejects_invalid_credentials(client):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "nobody@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"
