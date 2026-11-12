"""Products: anyone can browse the shop, only admins can change it."""
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Product

MUG = {
    "name": "Coffee mug",
    "description": "Holds coffee.",
    "price_cents": 1299,
    "stock": 5,
    "image_url": "https://example.com/mug.jpg",
}


def add_product(client, admin_headers, **changes) -> dict:
    r = client.post("/admin/products", headers=admin_headers, json={**MUG, **changes})
    assert r.status_code == 201
    return r.json()


def test_anyone_can_browse_the_shop(client, admin_headers):
    mug = add_product(client, admin_headers)

    # No login needed to look
    assert [p["name"] for p in client.get("/products").json()] == ["Coffee mug"]
    r = client.get(f"/products/{mug['id']}")
    assert r.status_code == 200
    assert r.json()["price_cents"] == 1299


def test_hidden_products_are_not_in_the_shop(client, admin_headers):
    hidden = add_product(client, admin_headers, name="Secret", is_active=False)
    add_product(client, admin_headers)

    assert [p["name"] for p in client.get("/products").json()] == ["Coffee mug"]
    assert client.get(f"/products/{hidden['id']}").status_code == 404
    # The admin still sees it
    admin_list = client.get("/admin/products", headers=admin_headers).json()
    assert {p["name"] for p in admin_list} == {"Coffee mug", "Secret"}


def test_unknown_product_is_404(client):
    assert client.get(f"/products/{uuid.uuid4()}").status_code == 404
    assert client.get("/products/not-a-uuid").status_code == 422


def test_only_admins_can_change_products(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)
    url = f"/admin/products/{mug['id']}"

    for headers, expected in [({}, 401), (auth_headers, 403)]:
        assert client.post("/admin/products", headers=headers, json=MUG).status_code == expected
        assert client.patch(url, headers=headers, json={"price_cents": 1}).status_code == expected
        assert client.delete(url, headers=headers).status_code == expected

    assert client.get(f"/products/{mug['id']}").json()["price_cents"] == 1299  # unchanged


def test_admin_can_edit_only_some_fields(client, admin_headers):
    mug = add_product(client, admin_headers)

    r = client.patch(
        f"/admin/products/{mug['id']}", headers=admin_headers, json={"price_cents": 999}
    )

    assert r.status_code == 200
    assert r.json()["price_cents"] == 999
    assert r.json()["name"] == "Coffee mug"  # everything else stays the same
    assert r.json()["stock"] == 5


def test_admin_can_remove_the_image(client, admin_headers):
    mug = add_product(client, admin_headers)

    r = client.patch(f"/admin/products/{mug['id']}", headers=admin_headers, json={"image_url": None})

    assert r.json()["image_url"] is None


def test_null_does_not_empty_a_required_field(client, admin_headers):
    mug = add_product(client, admin_headers)

    r = client.patch(f"/admin/products/{mug['id']}", headers=admin_headers, json={"name": None})

    assert r.status_code == 200
    assert r.json()["name"] == "Coffee mug"


def test_admin_can_delete_a_product(client, admin_headers):
    mug = add_product(client, admin_headers)
    url = f"/admin/products/{mug['id']}"

    assert client.delete(url, headers=admin_headers).status_code == 204
    assert client.get(f"/products/{mug['id']}").status_code == 404
    assert client.delete(url, headers=admin_headers).status_code == 404


@pytest.mark.parametrize(
    "bad",
    [
        {"price_cents": -1},
        {"stock": -1},
        {"price_cents": 12.99},  # cents must be a whole number
        {"name": ""},
        {"image_url": "javascript:alert(1)"},
        {"image_url": "not a link"},
    ],
)
def test_bad_product_data_is_refused(client, admin_headers, bad):
    r = client.post("/admin/products", headers=admin_headers, json={**MUG, **bad})
    assert r.status_code == 422


def test_database_refuses_negative_stock():
    # Even if the code had a bug, the database check stops a negative stock
    with SessionLocal() as db:
        db.add(Product(name="Broken", price_cents=100, stock=-1))
        with pytest.raises(IntegrityError):
            db.commit()


def test_website_may_send_patch_and_delete(client):
    """The browser asks first (CORS preflight) before it sends PATCH or DELETE."""
    r = client.options(
        "/admin/products/x",
        headers={"Origin": settings.frontend_origin, "Access-Control-Request-Method": "DELETE"},
    )
    assert r.status_code == 200
    assert "DELETE" in r.headers["access-control-allow-methods"]
    assert "PATCH" in r.headers["access-control-allow-methods"]
