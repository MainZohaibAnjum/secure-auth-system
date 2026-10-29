"""Too many requests from one IP address get a 429."""
from limits import parse

from app.core.config import settings
from app.core.rate_limit import limiter
from tests.conftest import PASSWORD


def test_signup_is_rate_limited(client):
    limiter.enabled = True
    allowed = parse(settings.rate_limit_signup).amount  # e.g. 3 for "3/minute"

    codes = [
        client.post("/auth/signup", json={"email": f"user{i}@example.com", "password": PASSWORD}).status_code
        for i in range(allowed + 1)
    ]

    assert codes == [201] * allowed + [429]


def test_login_is_rate_limited(client):
    limiter.enabled = True
    allowed = parse(settings.rate_limit_login).amount

    codes = [
        client.post("/auth/login", json={"email": f"nobody{i}@example.com", "password": "x"}).status_code
        for i in range(allowed + 1)
    ]

    assert codes == [401] * allowed + [429]
