"""Turning 2FA on and off, and logging in with a 6-digit code."""
import time

import pyotp
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import User


def enable_2fa(client, headers) -> pyotp.TOTP:
    """Run /setup and /enable like a real user would. Returns their authenticator."""
    secret = client.post("/auth/2fa/setup", headers=headers).json()["secret"]
    totp = pyotp.TOTP(secret)
    assert client.post("/auth/2fa/enable", headers=headers, json={"code": totp.now()}).status_code == 200
    return totp


def next_code(totp: pyotp.TOTP) -> str:
    """A code from the next 30-second window: still accepted, and not used yet."""
    return totp.at(time.time() + totp.interval)


def wrong_code(totp: pyotp.TOTP) -> str:
    """A 6-digit code that is definitely not valid right now."""
    valid = {totp.at(time.time() + drift * totp.interval) for drift in (-1, 0, 1)}
    return next(code for code in ("000000", "111111", "222222", "333333") if code not in valid)


def test_setup_and_enable(client, user, auth_headers):
    r = client.post("/auth/2fa/setup", headers=auth_headers)
    assert r.status_code == 200
    setup = r.json()
    assert setup["otpauth_uri"].startswith("otpauth://totp/")
    assert setup["qr_code_data_uri"].startswith("data:image/png;base64,")

    totp = pyotp.TOTP(setup["secret"])
    bad = client.post("/auth/2fa/enable", headers=auth_headers, json={"code": wrong_code(totp)})
    assert bad.status_code == 400

    good = client.post("/auth/2fa/enable", headers=auth_headers, json={"code": totp.now()})
    assert good.status_code == 200
    assert good.json()["totp_enabled"] is True


def test_secret_is_stored_encrypted(client, user, auth_headers):
    secret = client.post("/auth/2fa/setup", headers=auth_headers).json()["secret"]

    with SessionLocal() as db:
        stored = db.scalar(select(User.totp_secret_encrypted).where(User.email == user["email"]))

    assert stored and secret not in stored


def test_login_with_2fa_needs_a_code(client, user, auth_headers):
    totp = enable_2fa(client, auth_headers)

    # Step 1: the password alone gives only a challenge token
    r = client.post("/auth/login", json=user)
    body = r.json()
    assert body["requires_2fa"] is True
    assert body["access_token"] is None
    challenge = body["challenge_token"]

    # The challenge token is not an access token
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {challenge}"}).status_code == 401

    # Step 2: challenge token + code gives the real tokens
    code = next_code(totp)
    r = client.post("/auth/2fa/verify", json={"challenge_token": challenge, "code": code})
    assert r.status_code == 200
    assert r.json()["access_token"]
    assert client.cookies.get("refresh_token")

    # The same code can't be used twice
    replay = client.post("/auth/2fa/verify", json={"challenge_token": challenge, "code": code})
    assert replay.status_code == 401


def test_wrong_codes_lock_the_account(client, user, auth_headers):
    totp = enable_2fa(client, auth_headers)
    challenge = client.post("/auth/login", json=user).json()["challenge_token"]

    for _ in range(settings.max_failed_login_attempts):
        r = client.post("/auth/2fa/verify", json={"challenge_token": challenge, "code": wrong_code(totp)})
        assert r.status_code == 401

    # Locked: even a correct code is refused now
    r = client.post("/auth/2fa/verify", json={"challenge_token": challenge, "code": next_code(totp)})
    assert r.status_code == 401


def test_disable_needs_password_and_code(client, user, auth_headers):
    totp = enable_2fa(client, auth_headers)

    wrong_password = {"password": "wrong-password", "code": next_code(totp)}
    assert client.post("/auth/2fa/disable", headers=auth_headers, json=wrong_password).status_code == 400

    ok = {"password": user["password"], "code": next_code(totp)}
    r = client.post("/auth/2fa/disable", headers=auth_headers, json=ok)
    assert r.status_code == 200
    assert r.json()["totp_enabled"] is False

    # Back to a normal one-step login
    assert client.post("/auth/login", json=user).json()["access_token"]
