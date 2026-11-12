"""Roles: normal users and admins."""
from app.make_admin import main as make_admin



def test_new_users_are_normal_users(client, auth_headers):
    assert client.get("/auth/me", headers=auth_headers).json()["role"] == "user"


def test_signup_cannot_choose_its_own_role(client):
    sneaky = {"email": "sneaky@example.com", "password": "sneaky-long-password", "role": "admin"}
    assert client.post("/auth/signup", json=sneaky).json()["role"] == "user"


def test_admin_pages_need_login(client):
    assert client.get("/admin/users").status_code == 401


def test_normal_users_cannot_see_admin_pages(client, auth_headers):
    r = client.get("/admin/users", headers=auth_headers)

    assert r.status_code == 403
    assert r.json()["detail"] == "Admins only"


def test_admin_can_list_all_users(client, user, admin_headers):
    r = client.get("/admin/users", headers=admin_headers)

    assert r.status_code == 200
    users = {u["email"]: u for u in r.json()}
    assert users.keys() == {user["email"], "boss@example.com"}
    assert users["boss@example.com"]["role"] == "admin"
    assert users[user["email"]]["role"] == "user"
    assert all("password_hash" not in u for u in r.json())


def test_role_changes_work_straight_away(client, user, auth_headers):
    # The same access token, before and after: the role is checked in the database every time
    assert client.get("/admin/users", headers=auth_headers).status_code == 403

    make_admin([user["email"]])
    assert client.get("/admin/users", headers=auth_headers).status_code == 200

    make_admin([user["email"], "--remove"])
    assert client.get("/admin/users", headers=auth_headers).status_code == 403


def test_make_admin_with_unknown_email_fails(capsys):
    assert make_admin(["nobody@example.com"]) == 1
    assert "No user" in capsys.readouterr().out
