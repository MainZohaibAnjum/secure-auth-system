import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models import CartItem, Order, OrderItem, OrderStatus, Product, User
from app.schemas.order import OrderResponse

# Every route needs a login, and users only ever see their own orders
router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def checkout(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Order:
    """Turn the cart into an order. Everything happens together, or nothing does."""
    # Sorted by product id, so two checkouts at the same moment always lock the
    # products in the same order and can never wait for each other forever (deadlock)
    cart = db.scalars(
        select(CartItem).where(CartItem.user_id == user.id).order_by(CartItem.product_id)
    ).all()
    lines = [item for item in cart if item.product.is_active]  # hidden products can't be bought
    if not lines:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Your cart is empty")

    order = Order(user_id=user.id, status=OrderStatus.PAID.value, total_cents=0)
    for item in lines:
        # Take the items off the shelf in ONE database step:
        # "lower the stock, but only if there is enough left".
        # If two people buy the last mug at the same moment, the database lets only
        # one of them through, so the stock can never go below zero.
        taken = db.execute(
            update(Product)
            .where(
                Product.id == item.product_id,
                Product.is_active.is_(True),
                Product.stock >= item.quantity,
            )
            .values(stock=Product.stock - item.quantity)
            # Read the name and price from the very row we just changed
            .returning(Product.name, Product.price_cents)
        ).one_or_none()

        if taken is None:
            db.rollback()  # undo the stock already taken for earlier lines
            raise HTTPException(status.HTTP_400_BAD_REQUEST, _not_enough_message(db, item))

        order.items.append(
            OrderItem(
                product_id=item.product_id,
                product_name=taken.name,
                unit_price_cents=taken.price_cents,  # the server's price, never the browser's
                quantity=item.quantity,
            )
        )

    order.total_cents = sum(line.line_total_cents for line in order.items)
    db.add(order)
    # Payment is pretend for now: the order counts as paid straight away (step 29: Stripe)
    db.execute(delete(CartItem).where(CartItem.user_id == user.id))
    db.commit()
    db.refresh(order)  # read the saved order back, so its lines come in the usual order
    return order


@router.get("",response_model=list[OrderResponse])
def list_my_orders(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Order]:
    """The logged-in user's orders, newest first."""
    return list(
        db.scalars(
            select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc())
        )
    )


@router.get("/{order_id}", response_model=OrderResponse)
def get_my_order(
    order_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> Order:
    order = db.get(Order, order_id)
    # Someone else's order looks exactly like one that doesn't exist
    if order is None or order.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


def _not_enough_message(db: Session, item: CartItem) -> str:
    product = db.get(Product, item.product_id)
    if product is None or not product.is_active:
        return "A product in your cart is no longer for sale. Please check your cart."
    if product.stock == 0:
        return f"Sorry, {product.name} is sold out. Please remove it from your cart."
    return f"Sorry, only {product.stock} of {product.name} left. Please change your cart."
