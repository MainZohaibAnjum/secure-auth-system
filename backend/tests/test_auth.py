"""Signup, login, /auth/me and account lockout."""
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import User
from tests.conftest import PASSWORD


def test_signup_creates_user(client):
    r = client.post("/auth/signup", json={"email": "Bob@Example.com", "password": PASSWORD})

    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "bob@example.com"  # stored in lowercase
    assert body["totp_enabled"] is False
    assert "password" not in body and "password_hash" not in body


def test_password_is_stored_hashed(client, user):
    with SessionLocal() as db:
        stored = db.scalar(select(User.password_hash).where(User.email == user["email"]))

    assert stored != user["password"]
    assert stored.startswith("$argon2id$")


def test_signup_duplicate_email_is_rejected(client, user):
    r = client.post("/auth/signup", json=user)
    assert r.status_code == 409


def test_signup_rejects_short_password(client):
    r = client.post("/auth/signup", json={"email": "bob@example.com", "password": "short"})
    assert r.status_code == 422


def test_login_returns_token_and_refresh_cookie(client, user):
    r = client.post("/auth/login", json=user)

    assert r.status_code == 200
    assert r.json()["access_token"]
    cookie = r.headers["set-cookie"]
    assert "refresh_token=" in cookie
    assert "HttpOnly" in cookie
    assert "Path=/auth" in cookie


def test_wrong_password_and_unknown_email_look_the_same(client, user):
    wrong_password = client.post("/auth/login", json={**user, "password": "wrong-password"})
    unknown_email = client.post("/auth/login", json={**user, "email": "nobody@example.com"})

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()  # attackers can't tell which was wrong


def test_me_requires_a_valid_token(client, auth_headers):
    assert client.get("/auth/me", headers=auth_headers).status_code == 200
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer not-a-token"}).status_code == 401


def test_account_locks_after_too_many_wrong_passwords(client, user):
    for _ in range(settings.max_failed_login_attempts):
        client.post("/auth/login", json={**user, "password": "wrong-password"})

    # Even the correct password is refused while the account is locked
    assert client.post("/auth/login", json=user).status_code == 401
