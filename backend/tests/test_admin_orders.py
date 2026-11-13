"""Order statuses: admins move orders on; cancelling puts the items back in stock."""
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionLocal
from app.models import Order
from app.models.order import OrderStatus
from app.services.orders import change_status
from tests.test_cart import PEN, other_user_headers
from tests.test_orders import add_to_cart, stock_of
from tests.test_products import add_product


def place_order(client, headers, product, quantity=1) -> dict:
    add_to_cart(client, headers, product, quantity)
    r = client.post("/orders", headers=headers)
    assert r.status_code == 201
    return r.json()


def set_status(client, admin_headers, order, new_status):
    return client.patch(
        f"/admin/orders/{order['id']}", headers=admin_headers, json={"status": new_status}
    )


def test_only_admins_can_manage_orders(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)
    order = place_order(client, auth_headers, mug)

    for headers, expected in [({}, 401), (auth_headers, 403)]:
        assert client.get("/admin/orders", headers=headers).status_code == expected
        assert set_status(client, headers, order, "shipped").status_code == expected

    # Nothing changed
    assert client.get(f"/orders/{order['id']}", headers=auth_headers).json()["status"] == "paid"


def test_admin_sees_every_customers_orders(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)
    first = place_order(client, auth_headers, mug)
    second = place_order(client, other_user_headers(client), mug)

    orders = client.get("/admin/orders", headers=admin_headers).json()

    assert [(o["id"], o["user_email"]) for o in orders] == [
        (second["id"], "bob@example.com"),  # newest first
        (first["id"], "alice@example.com"),
    ]


def test_admin_can_filter_by_status(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)
    shipped = place_order(client, auth_headers, mug)
    still_paid = place_order(client, auth_headers, mug)
    set_status(client, admin_headers, shipped, "shipped")

    def ids(status):
        r = client.get(f"/admin/orders?status={status}", headers=admin_headers)
        return [o["id"] for o in r.json()]

    assert ids("paid") == [still_paid["id"]]
    assert ids("shipped") == [shipped["id"]]
    assert ids("delivered") == []
    assert client.get("/admin/orders?status=lost", headers=admin_headers).status_code == 422


def test_ship_then_deliver(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)
    order = place_order(client, auth_headers, mug)

    r = set_status(client, admin_headers, order, "shipped")
    assert r.status_code == 200
    assert r.json()["status"] == "shipped"

    assert set_status(client, admin_headers, order, "delivered").json()["status"] == "delivered"
    # The customer sees it too
    assert client.get(f"/orders/{order['id']}", headers=auth_headers).json()["status"] == "delivered"
    assert stock_of(client, mug) == 4  # shipping doesn't touch the stock


@pytest.mark.parametrize(
    "steps, refused",
    [
        ([], "delivered"),  # paid can't skip shipping
        ([], "paid"),  # nothing moves to the status it already has
        (["shipped"], "cancelled"),  # too late to cancel once it's on its way
        (["shipped"], "paid"),  # never backwards
        (["shipped", "delivered"], "shipped"),  # delivered is final
        (["cancelled"], "shipped"),  # cancelled is final
    ],
)
def test_orders_only_move_forward(client, auth_headers, admin_headers, steps, refused):
    mug = add_product(client, admin_headers)
    order = place_order(client, auth_headers, mug)
    for step in steps:
        assert set_status(client, admin_headers, order, step).status_code == 200

    r = set_status(client, admin_headers, order, refused)

    assert r.status_code == 409
    assert "can't be changed" in r.json()["detail"]


def test_unknown_status_or_order_is_refused(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)
    order = place_order(client, auth_headers, mug)

    assert set_status(client, admin_headers, order, "lost").status_code == 422
    assert set_status(client, admin_headers, {"id": str(uuid.uuid4())}, "shipped").status_code == 404


def test_admin_cancel_puts_items_back_in_stock(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)  # stock 5
    pen = add_product(client, admin_headers, **PEN)  # stock 100
    add_to_cart(client, auth_headers, mug, 2)
    add_to_cart(client, auth_headers, pen, 10)
    order = client.post("/orders", headers=auth_headers).json()
    assert (stock_of(client, mug), stock_of(client, pen)) == (3, 90)

    r = set_status(client, admin_headers, order, "cancelled")

    assert r.json()["status"] == "cancelled"
    assert (stock_of(client, mug), stock_of(client, pen)) == (5, 100)


def test_cancel_skips_deleted_products(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)
    order = place_order(client, auth_headers, mug)
    client.delete(f"/admin/products/{mug['id']}", headers=admin_headers)

    r = set_status(client, admin_headers, order, "cancelled")

    assert r.status_code == 200  # nothing to put back, but the cancel still works


def test_customer_can_cancel_their_own_paid_order(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)
    order = place_order(client, auth_headers, mug, 2)

    r = client.post(f"/orders/{order['id']}/cancel", headers=auth_headers)

    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"
    assert stock_of(client, mug) == 5
    # Cancelling again does nothing, and the stock isn't put back twice
    assert client.post(f"/orders/{order['id']}/cancel", headers=auth_headers).status_code == 409
    assert stock_of(client, mug) == 5


def test_customer_cannot_cancel_after_shipping(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)
    order = place_order(client, auth_headers, mug)
    set_status(client, admin_headers, order, "shipped")

    r = client.post(f"/orders/{order['id']}/cancel", headers=auth_headers)

    assert r.status_code == 409
    assert r.json()["detail"] == "A shipped order can't be changed to cancelled"


def test_customer_cannot_cancel_someone_elses_order(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)
    order = place_order(client, auth_headers, mug)

    r = client.post(f"/orders/{order['id']}/cancel", headers=other_user_headers(client))

    assert r.status_code == 404
    assert stock_of(client, mug) == 4  # still bought


def test_two_cancels_at_the_same_moment_restock_only_once(client, auth_headers, admin_headers):
    """The admin opens the order, then the customer cancels it before the admin clicks."""
    mug = add_product(client, admin_headers)
    order = place_order(client, auth_headers, mug, 2)

    with SessionLocal() as db:
        admins_view = db.get(Order, uuid.UUID(order["id"]))  # still says "paid"
        client.post(f"/orders/{order['id']}/cancel", headers=auth_headers)  # customer is faster

        with pytest.raises(HTTPException) as refused:
            change_status(db, admins_view, OrderStatus.CANCELLED)

    assert refused.value.status_code == 409
    assert "Someone else changed this order" in refused.value.detail
    assert stock_of(client, mug) == 5  # put back once, not twice


def test_database_refuses_an_unknown_status(client, auth_headers, admin_headers):
    mug = add_product(client, admin_headers)
    order = place_order(client, auth_headers, mug)

    with SessionLocal() as db:
        with pytest.raises(IntegrityError):
            db.execute(update(Order).where(Order.id == uuid.UUID(order["id"])).values(status="lost"))
            db.commit()
