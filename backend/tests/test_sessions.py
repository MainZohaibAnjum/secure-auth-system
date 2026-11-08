"""Session management: list your devices and log them out."""
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import PASSWORD


def login_device(user, device_name: str) -> tuple[TestClient, dict]:
    """Log in from a separate "device" (its own cookie jar and User-Agent)."""
    device = TestClient(app, headers={"User-Agent": device_name})
    token = device.post("/auth/login", json=user).json()["access_token"]
    return device, {"Authorization": f"Bearer {token}"}


def test_lists_every_logged_in_device(user):
    laptop, laptop_auth = login_device(user, "Laptop")
    phone, _ = login_device(user, "Phone")

    sessions = laptop.get("/auth/sessions", headers=laptop_auth).json()

    assert sorted(s["user_agent"] for s in sessions) == ["Laptop", "Phone"]
    current = [s["user_agent"] for s in sessions if s["current"]]
    assert current == ["Laptop"]  # each device sees itself marked as current


def test_refreshing_keeps_the_same_device_entry(user):
    laptop, laptop_auth = login_device(user, "Laptop")
    before = laptop.get("/auth/sessions", headers=laptop_auth).json()

    laptop.post("/auth/refresh")  # rotates the token (a new database row)
    after = laptop.get("/auth/sessions", headers=laptop_auth).json()

    assert len(after) == 1
    assert after[0]["id"] == before[0]["id"]
    assert after[0]["signed_in_at"] == before[0]["signed_in_at"]
    assert after[0]["last_active_at"] >= before[0]["last_active_at"]


def test_revoke_logs_out_that_device(user):
    laptop, laptop_auth = login_device(user, "Laptop")
    phone, _ = login_device(user, "Phone")
    phone_id = next(
        s["id"] for s in laptop.get("/auth/sessions", headers=laptop_auth).json() if not s["current"]
    )

    assert laptop.post(f"/auth/sessions/{phone_id}/revoke", headers=laptop_auth).status_code == 204

    assert phone.post("/auth/refresh").status_code == 401  # the phone is logged out
    assert laptop.post("/auth/refresh").status_code == 200  # the laptop is not
    assert len(laptop.get("/auth/sessions", headers=laptop_auth).json()) == 1


def test_cannot_revoke_the_current_device(user):
    laptop, laptop_auth = login_device(user, "Laptop")
    my_id = laptop.get("/auth/sessions", headers=laptop_auth).json()[0]["id"]

    r = laptop.post(f"/auth/sessions/{my_id}/revoke", headers=laptop_auth)

    assert r.status_code == 400


def test_cannot_revoke_another_users_session(client, user):
    victim, victim_auth = login_device(user, "Victim")
    victim_id = victim.get("/auth/sessions", headers=victim_auth).json()[0]["id"]

    attacker_creds = {"email": "mallory@example.com", "password": PASSWORD}
    client.post("/auth/signup", json=attacker_creds)
    attacker, attacker_auth = login_device(attacker_creds, "Attacker")

    r = attacker.post(f"/auth/sessions/{victim_id}/revoke", headers=attacker_auth)

    assert r.status_code == 404  # looks the same as an ID that doesn't exist
    assert victim.post("/auth/refresh").status_code == 200  # victim still logged in
    assert [s["user_agent"] for s in attacker.get("/auth/sessions", headers=attacker_auth).json()] == [
        "Attacker"
    ]  # and the attacker can't see the victim's devices


def test_revoke_others_keeps_only_this_device(user):
    laptop, laptop_auth = login_device(user, "Laptop")
    phone, _ = login_device(user, "Phone")
    tablet, _ = login_device(user, "Tablet")

    r = laptop.post("/auth/sessions/revoke-others", headers=laptop_auth)

    assert r.json() == {"revoked": 2}
    assert phone.post("/auth/refresh").status_code == 401
    assert tablet.post("/auth/refresh").status_code == 401
    assert laptop.post("/auth/refresh").status_code == 200


def test_logout_removes_the_device_from_the_list(user):
    laptop, laptop_auth = login_device(user, "Laptop")
    phone, _ = login_device(user, "Phone")

    phone.post("/auth/logout")

    sessions = laptop.get("/auth/sessions", headers=laptop_auth).json()
    assert [s["user_agent"] for s in sessions] == ["Laptop"]


def test_sessions_need_an_access_token(client):
    assert client.get("/auth/sessions").status_code == 401
    assert client.post("/auth/sessions/revoke-others").status_code == 401
