"""Checkout and orders: the cart becomes an order, stock goes down, all or nothing."""
import uuid

from tests.test_cart import PEN, other_user_headers
from tests.test_products import add_product


def add_to_cart(client, headers, product, quantity=1):
    r = client.post(
        "/cart/items", headers=headers, json={"product_id": product["id"], "quantity": quantity}
    )
    assert r.status_code == 200


def stock_of(client, product) -> int:
    return client.get(f"/products/{product['id']}").json()["stock"]


def test_orders_need_login(client):
    assert client.post("/orders").status_code == 401
    assert client.get("/orders").status_code == 401
    assert client.get(f"/orders/{uuid.uuid4()}").status_code == 401


def test_cannot_check_out_an_empty_cart(client, auth_headers):
    r = client.post("/orders", headers=auth_headers)

    assert r.status_code == 400
    assert r.json()["detail"] == "Your cart is empty"


def test_checkout_makes_an_order(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)  # 12.99, stock 5
    pen = add_product(client, admin_headers, **PEN)  # 2.50, stock 100
    add_to_cart(client, auth_headers, mug, 2)
    add_to_cart(client, auth_headers, pen, 3)

    r = client.post("/orders", headers=auth_headers)

    assert r.status_code == 201
    order = r.json()
    assert order["status"] == "paid"
    assert order["total_cents"] == 2 * 1299 + 3 * 250
    assert [(i["product_name"], i["quantity"], i["unit_price_cents"]) for i in order["items"]] == [
        ("Coffee mug", 2, 1299),
        ("Pen", 3, 250),
    ]
    # The stock went down, and the cart is empty again
    assert stock_of(client, mug) == 3
    assert stock_of(client, pen) == 97
    assert client.get("/cart", headers=auth_headers).json()["items"] == []


def test_checking_out_twice_does_not_buy_twice(client, auth_headers, admin_headers):
    """A double click on "Checkout" must not make two orders."""
    mug = add_product(client, admin_headers)
    add_to_cart(client, auth_headers, mug)

    assert client.post("/orders", headers=auth_headers).status_code == 201
    assert client.post("/orders", headers=auth_headers).status_code == 400  # cart is empty now

    assert len(client.get("/orders", headers=auth_headers).json()) == 1
    assert stock_of(client, mug) == 4


def test_not_enough_stock_stops_the_whole_order(client, auth_headers, admin_headers):
    pen = add_product(client, admin_headers, **PEN)
    mug = add_product(client, admin_headers)
    add_to_cart(client, auth_headers, pen, 10)
    add_to_cart(client, auth_headers, mug, 3)
    # The stock drops after it was put in the cart (someone else bought some)
    client.patch(f"/admin/products/{mug['id']}", headers=admin_headers, json={"stock": 2})

    r = client.post("/orders", headers=auth_headers)

    assert r.status_code == 400
    assert r.json()["detail"] == "Sorry, only 2 of Coffee mug left. Please change your cart."
    # All or nothing: the pens were NOT taken either, no order, cart unchanged
    assert stock_of(client, pen) == 100
    assert stock_of(client, mug) == 2
    assert client.get("/orders", headers=auth_headers).json() == []
    assert len(client.get("/cart", headers=auth_headers).json()["items"]) == 2


def test_only_one_person_gets_the_last_item(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers, stock=1)
    bob = other_user_headers(client)
    add_to_cart(client, auth_headers, mug)
    add_to_cart(client, bob, mug)  # both have the last mug in their cart

    assert client.post("/orders", headers=auth_headers).status_code == 201
    r = client.post("/orders", headers=bob)

    assert r.status_code == 400
    assert r.json()["detail"] == "Sorry, Coffee mug is sold out. Please remove it from your cart."
    assert stock_of(client, mug) == 0  # never below zero


def test_hidden_products_are_not_bought(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)
    pen = add_product(client, admin_headers, **PEN)
    add_to_cart(client, auth_headers, mug)
    add_to_cart(client, auth_headers, pen)
    client.patch(f"/admin/products/{mug['id']}", headers=admin_headers, json={"is_active": False})

    r = client.post("/orders", headers=auth_headers)

    assert [i["product_name"] for i in r.json()["items"]] == ["Pen"]
    assert r.json()["total_cents"] == 250


def test_order_keeps_the_price_and_name_from_checkout_time(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)
    add_to_cart(client, auth_headers, mug)
    order = client.post("/orders", headers=auth_headers).json()

    # Later the admin changes the price and name, then deletes the product
    url = f"/admin/products/{mug['id']}"
    client.patch(url, headers=admin_headers, json={"price_cents": 1, "name": "Cheap mug"})
    client.delete(url, headers=admin_headers)

    saved = client.get(f"/orders/{order['id']}", headers=auth_headers).json()
    assert saved["total_cents"] == 1299
    assert saved["items"][0]["product_name"] == "Coffee mug"
    assert saved["items"][0]["unit_price_cents"] == 1299
    assert saved["items"][0]["product_id"] is None  # the product itself is gone


def test_users_only_see_their_own_orders(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)
    add_to_cart(client, auth_headers, mug)
    order = client.post("/orders", headers=auth_headers).json()
    bob = other_user_headers(client)

    assert client.get("/orders", headers=bob).json() == []
    assert client.get(f"/orders/{order['id']}", headers=bob).status_code == 404
    # Alice can see it
    assert client.get(f"/orders/{order['id']}", headers=auth_headers).status_code == 200


def test_orders_are_listed_newest_first(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)
    pen = add_product(client, admin_headers, **PEN)
    add_to_cart(client, auth_headers, mug)
    first = client.post("/orders", headers=auth_headers).json()
    add_to_cart(client, auth_headers, pen)
    second = client.post("/orders", headers=auth_headers).json()

    ids = [o["id"] for o in client.get("/orders", headers=auth_headers).json()]

    assert ids == [second["id"], first["id"]]


def test_unknown_order_is_404(client, auth_headers):
    assert client.get(f"/orders/{uuid.uuid4()}", headers=auth_headers).status_code == 404
