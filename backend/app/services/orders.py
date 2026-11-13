from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import Order, Product
from app.models.order import NEXT_STATUSES, OrderStatus


def change_status(db: Session, order: Order, new_status: OrderStatus) -> Order:
    """Move an order to a new status. Cancelling puts the items back in stock.

    Everything happens in one transaction: the status change and the restock
    both happen, or neither does.
    """
    old_status = OrderStatus(order.status)
    if new_status not in NEXT_STATUSES[old_status]:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"A {old_status.value} order can't be changed to {new_status.value}",
        )

    # Change it ONLY if it still has the status we just read. If two admins click
    # "Cancel" at the same moment, the database lets only one of them through,
    # so the items can never be put back in stock twice.
    changed = db.execute(
        update(Order)
        .where(Order.id == order.id, Order.status == old_status.value)
        .values(status=new_status.value)
    ).rowcount
    if changed == 0:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Someone else changed this order a moment ago. Please reload and try again.",
        )

    if new_status == OrderStatus.CANCELLED:
        for item in order.items:
            if item.product_id is None:
                continue  # the product was deleted, so there's nothing to put back
            # "stock = stock + n" is worked out inside the database, so a checkout
            # happening at the same time can't make us lose an update
            db.execute(
                update(Product)
                .where(Product.id == item.product_id)
                .values(stock=Product.stock + item.quantity)
            )

    db.commit()
    db.refresh(order)
    return order
