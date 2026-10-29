"""Refresh-token rotation, reuse detection and logout."""
from fastapi.testclient import TestClient

from app.main import app


def test_refresh_gives_new_access_token_and_new_cookie(client, user):
    client.post("/auth/login", json=user)
    old_cookie = client.cookies.get("refresh_token")

    r = client.post("/auth/refresh")

    assert r.status_code == 200
    assert r.json()["access_token"]
    assert client.cookies.get("refresh_token") != old_cookie  # rotated


def test_refresh_without_cookie_fails(client):
    assert client.post("/auth/refresh").status_code == 401


def test_reusing_an_old_refresh_token_ends_the_whole_session(client, user):
    client.post("/auth/login", json=user)
    stolen = client.cookies.get("refresh_token")
    client.post("/auth/refresh")  # the real user refreshes; "stolen" is now an old token

    attacker = TestClient(app, cookies={"refresh_token": stolen})
    assert attacker.post("/auth/refresh").status_code == 401

    # Reuse was detected, so the real user's newer token is revoked too
    assert client.post("/auth/refresh").status_code == 401


def test_logout_revokes_the_refresh_token(client, user):
    client.post("/auth/login", json=user)
    token = client.cookies.get("refresh_token")

    assert client.post("/auth/logout").status_code == 204

    after_logout = TestClient(app, cookies={"refresh_token": token})
    assert after_logout.post("/auth/refresh").status_code == 401
