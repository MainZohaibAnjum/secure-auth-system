"""2FA recovery codes: one-time backup codes for when the phone is lost."""
import re

import pyotp
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import RecoveryCode
from tests.test_two_factor import next_code


def enable_2fa(client, headers) -> tuple[pyotp.TOTP, list[str]]:
    """Turn 2FA on. Returns the authenticator and the recovery codes shown once."""
    secret = client.post("/auth/2fa/setup", headers=headers).json()["secret"]
    totp = pyotp.TOTP(secret)
    r = client.post("/auth/2fa/enable", headers=headers, json={"code": totp.now()})
    assert r.status_code == 200
    return totp, r.json()["recovery_codes"]


def log_in_with_code(client, user, code: str):
    """Password step, then the 2FA step with the given code."""
    challenge = client.post("/auth/login", json=user).json()["challenge_token"]
    return client.post("/auth/2fa/verify", json={"challenge_token": challenge, "code": code})


def remaining(client, headers) -> int:
    return client.get("/auth/2fa/recovery-codes", headers=headers).json()["remaining"]


def test_enabling_2fa_gives_recovery_codes(client, user, auth_headers):
    _, codes = enable_2fa(client, auth_headers)

    assert len(codes) == settings.recovery_code_count
    assert len(set(codes)) == len(codes)  # all different
    assert all(re.fullmatch(r"[A-Z2-9]{4}(-[A-Z2-9]{4}){3}", code) for code in codes)
    assert remaining(client, auth_headers) == settings.recovery_code_count


def test_codes_are_stored_hashed(client, user, auth_headers):
    _, codes = enable_2fa(client, auth_headers)

    with SessionLocal() as db:
        stored = db.scalars(select(RecoveryCode.code_hash)).all()

    assert len(stored) == len(codes)
    for code in codes:
        assert all(code not in value and code.replace("-", "") not in value for value in stored)


def test_log_in_with_a_recovery_code_only_once(client, user, auth_headers):
    _, codes = enable_2fa(client, auth_headers)

    r = log_in_with_code(client, user, codes[0])
    assert r.status_code == 200
    assert r.json()["access_token"]
    assert remaining(client, auth_headers) == settings.recovery_code_count - 1

    # The same code can never be used again
    assert log_in_with_code(client, user, codes[0]).status_code == 401


def test_recovery_code_ignores_case_dashes_and_spaces(client, user, auth_headers):
    _, codes = enable_2fa(client, auth_headers)
    messy = " " + codes[0].replace("-", " ").lower() + " "

    assert log_in_with_code(client, user, messy).status_code == 200


def test_wrong_recovery_code_is_refused(client, user, auth_headers):
    enable_2fa(client, auth_headers)

    assert log_in_with_code(client, user, "AAAA-BBBB-CCCC-DDDD").status_code == 401
    assert remaining(client, auth_headers) == settings.recovery_code_count


def test_new_codes_replace_the_old_ones(client, user, auth_headers):
    totp, old_codes = enable_2fa(client, auth_headers)

    wrong_password = {"password": "wrong-password", "code": next_code(totp)}
    r = client.post("/auth/2fa/recovery-codes", headers=auth_headers, json=wrong_password)
    assert r.status_code == 400

    ok = {"password": user["password"], "code": next_code(totp)}
    r = client.post("/auth/2fa/recovery-codes", headers=auth_headers, json=ok)
    assert r.status_code == 200
    new_codes = r.json()["recovery_codes"]
    assert set(new_codes).isdisjoint(old_codes)

    assert log_in_with_code(client, user, old_codes[0]).status_code == 401
    assert log_in_with_code(client, user, new_codes[0]).status_code == 200


def test_wrong_password_does_not_use_up_a_code(client, user, auth_headers):
    _, codes = enable_2fa(client, auth_headers)

    bad = {"password": "wrong-password", "code": codes[0]}
    assert client.post("/auth/2fa/disable", headers=auth_headers, json=bad).status_code == 400

    assert remaining(client, auth_headers) == settings.recovery_code_count
    assert log_in_with_code(client, user, codes[0]).status_code == 200


def test_lost_phone_can_turn_off_2fa_with_a_recovery_code(client, user, auth_headers):
    _, codes = enable_2fa(client, auth_headers)

    r = client.post(
        "/auth/2fa/disable",
        headers=auth_headers,
        json={"password": user["password"], "code": codes[0]},
    )

    assert r.status_code == 200
    assert r.json()["totp_enabled"] is False
    with SessionLocal() as db:
        assert db.scalars(select(RecoveryCode)).all() == []  # all codes deleted


def test_recovery_codes_need_an_access_token(client):
    assert client.get("/auth/2fa/recovery-codes").status_code == 401
    assert client.post("/auth/2fa/recovery-codes", json={"password": "x", "code": "123456"}).status_code == 401


def test_2fa_app_codes_still_work(client, user, auth_headers):
    totp, _ = enable_2fa(client, auth_headers)

    assert log_in_with_code(client, user, next_code(totp)).status_code == 200
