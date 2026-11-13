"""Cart: each logged-in user has their own cart; the server checks stock and works out prices."""
import uuid

from tests.test_products import MUG, add_product

PEN = {**MUG, "name": "Pen", "price_cents": 250, "stock": 100}


def other_user_headers(client) -> dict:
    """A second, ordinary user (bob)."""
    bob = {"email": "bob@example.com", "password": "bob-long-password-1"}
    assert client.post("/auth/signup", json=bob).status_code == 201
    token = client.post("/auth/login", json=bob).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_cart_needs_login(client):
    assert client.get("/cart").status_code == 401
    r = client.post("/cart/items", json={"product_id": str(uuid.uuid4())})
    assert r.status_code == 401


def test_new_cart_is_empty(client, auth_headers):
    r = client.get("/cart", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"items": [], "total_cents": 0}


def test_add_items_and_server_works_out_the_total(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)  # 12.99
    pen = add_product(client, admin_headers, **PEN)  # 2.50

    client.post("/cart/items", headers=auth_headers, json={"product_id": mug["id"], "quantity": 2})
    r = client.post("/cart/items", headers=auth_headers, json={"product_id": pen["id"]})

    assert r.status_code == 200
    cart = r.json()
    assert [(line["product"]["name"], line["quantity"]) for line in cart["items"]] == [
        ("Coffee mug", 2),
        ("Pen", 1),
    ]
    assert cart["items"][0]["line_total_cents"] == 2598
    assert cart["total_cents"] == 2598 + 250


def test_adding_the_same_product_again_raises_the_quantity(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)

    client.post("/cart/items", headers=auth_headers, json={"product_id": mug["id"]})
    r = client.post("/cart/items", headers=auth_headers, json={"product_id": mug["id"], "quantity": 2})

    assert len(r.json()["items"]) == 1
    assert r.json()["items"][0]["quantity"] == 3


def test_cannot_add_more_than_the_stock(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)  # stock 5

    r = client.post("/cart/items", headers=auth_headers, json={"product_id": mug["id"], "quantity": 6})
    assert r.status_code == 400
    assert r.json()["detail"] == "Sorry, only 5 left in stock"

    # 4 is fine, but 4 + 2 more is too many
    client.post("/cart/items", headers=auth_headers, json={"product_id": mug["id"], "quantity": 4})
    r = client.post("/cart/items", headers=auth_headers, json={"product_id": mug["id"], "quantity": 2})
    assert r.status_code == 400
    assert client.get("/cart", headers=auth_headers).json()["items"][0]["quantity"] == 4


def test_cannot_add_a_sold_out_product(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers, stock=0)

    r = client.post("/cart/items", headers=auth_headers, json={"product_id": mug["id"]})

    assert r.status_code == 400
    assert r.json()["detail"] == "Sorry, this product is sold out"


def test_cannot_add_hidden_or_unknown_products(client, auth_headers, admin_headers):
    hidden = add_product(client, admin_headers, is_active=False)

    for product_id in [hidden["id"], str(uuid.uuid4())]:
        r = client.post("/cart/items", headers=auth_headers, json={"product_id": product_id})
        assert r.status_code == 404


def test_change_the_quantity(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)
    client.post("/cart/items", headers=auth_headers, json={"product_id": mug["id"]})
    url = f"/cart/items/{mug['id']}"

    r = client.patch(url, headers=auth_headers, json={"quantity": 4})
    assert r.status_code == 200
    assert r.json()["items"][0]["quantity"] == 4
    assert r.json()["total_cents"] == 4 * 1299

    assert client.patch(url, headers=auth_headers, json={"quantity": 6}).status_code == 400
    assert client.patch(url, headers=auth_headers, json={"quantity": 0}).status_code == 422


def test_cannot_change_a_product_that_is_not_in_the_cart(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)

    r = client.patch(f"/cart/items/{mug['id']}", headers=auth_headers, json={"quantity": 1})

    assert r.status_code == 404


def test_remove_one_item_and_empty_the_cart(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)
    pen = add_product(client, admin_headers, **PEN)
    for product in (mug, pen):
        client.post("/cart/items", headers=auth_headers, json={"product_id": product["id"]})

    r = client.delete(f"/cart/items/{mug['id']}", headers=auth_headers)
    assert [line["product"]["name"] for line in r.json()["items"]] == ["Pen"]
    assert client.delete(f"/cart/items/{mug['id']}", headers=auth_headers).status_code == 404

    assert client.delete("/cart", headers=auth_headers).status_code == 204
    assert client.get("/cart", headers=auth_headers).json()["items"] == []


def test_each_user_only_sees_their_own_cart(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)
    client.post("/cart/items", headers=auth_headers, json={"product_id": mug["id"]})
    bob = other_user_headers(client)

    # Bob's cart is empty, and he can't change or remove Alice's line
    assert client.get("/cart", headers=bob).json()["items"] == []
    url = f"/cart/items/{mug['id']}"
    assert client.patch(url, headers=bob, json={"quantity": 2}).status_code == 404
    assert client.delete(url, headers=bob).status_code == 404
    client.delete("/cart", headers=bob)

    assert client.get("/cart", headers=auth_headers).json()["items"][0]["quantity"] == 1


def test_cart_uses_the_current_price(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)
    client.post("/cart/items", headers=auth_headers, json={"product_id": mug["id"]})

    client.patch(f"/admin/products/{mug['id']}", headers=admin_headers, json={"price_cents": 999})

    assert client.get("/cart", headers=auth_headers).json()["total_cents"] == 999


def test_hidden_or_deleted_products_drop_out_of_the_cart(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)
    pen = add_product(client, admin_headers, **PEN)
    for product in (mug, pen):
        client.post("/cart/items", headers=auth_headers, json={"product_id": product["id"]})

    client.patch(f"/admin/products/{mug['id']}", headers=admin_headers, json={"is_active": False})
    client.delete(f"/admin/products/{pen['id']}", headers=admin_headers)

    assert client.get("/cart", headers=auth_headers).json() == {"items": [], "total_cents": 0}


def test_client_cannot_send_its_own_price(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)

    r = client.post(
        "/cart/items",
        headers=auth_headers,
        json={"product_id": mug["id"], "quantity": 1, "price_cents": 1},
    )

    # The extra field is ignored: the price always comes from the database
    assert r.json()["total_cents"] == 1299
