from datetime import UTC, datetime, timedelta

import jwt

from tests.conftest import register_and_login


def test_register_login_me(client):
    headers = register_and_login(client, "Carol@Example.com")
    r = client.get("/api/v1/auth/me", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "carol@example.com"
    assert body["role"] == "user"
    assert "hashed_password" not in body


def test_duplicate_email_rejected(client):
    register_and_login(client, "dup@example.com")
    r = client.post(
        "/api/v1/auth/register", json={"email": "DUP@example.com", "password": "password123"}
    )
    assert r.status_code == 409


def test_wrong_password_and_unknown_user_give_same_error(client):
    register_and_login(client, "dave@example.com")
    wrong = client.post(
        "/api/v1/auth/login", data={"username": "dave@example.com", "password": "nope-nope"}
    )
    unknown = client.post(
        "/api/v1/auth/login", data={"username": "ghost@example.com", "password": "nope-nope"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_short_password_rejected(client):
    r = client.post("/api/v1/auth/register", json={"email": "e@example.com", "password": "short"})
    assert r.status_code == 422


def test_protected_route_requires_token(client):
    assert client.get("/api/v1/documents").status_code == 401
    bad = {"Authorization": "Bearer not-a-jwt"}
    assert client.get("/api/v1/documents", headers=bad).status_code == 401


def test_expired_token_rejected(client, settings):
    register_and_login(client, "frank@example.com")
    me = client.post(
        "/api/v1/auth/login", data={"username": "frank@example.com", "password": "password123"}
    )
    sub = jwt.decode(me.json()["access_token"], options={"verify_signature": False})["sub"]
    expired = jwt.encode(
        {"sub": sub, "type": "access", "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401


def test_admin_role_and_admin_endpoint(client):
    user_headers = register_and_login(client, "plain@example.com")
    admin_headers = register_and_login(client, "admin@example.com")  # FIRST_ADMIN_EMAIL in tests
    assert client.get("/api/v1/admin/stats", headers=user_headers).status_code == 403
    r = client.get("/api/v1/admin/stats", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["users"] == 2
