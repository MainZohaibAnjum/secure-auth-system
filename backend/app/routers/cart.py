import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models import CartItem, Product, User
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartLine, CartResponse

# Every route needs a login, and only ever touches the logged-in user's own cart
router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=CartResponse)
def get_cart(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CartResponse:
    return _build_cart(db, user)


@router.post("/items", response_model=CartResponse)
def add_item(
    data: CartItemAdd, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CartResponse:
    product = _get_for_sale_or_404(db, data.product_id)
    item = _find_item(db, user, product.id)

    # Already in the cart? Raise the quantity instead of making a second line.
    new_quantity = data.quantity + (item.quantity if item else 0)
    _check_stock(product, new_quantity)

    if item:
        item.quantity = new_quantity
    else:
        db.add(CartItem(user_id=user.id, product_id=product.id, quantity=new_quantity))
    db.commit()
    return _build_cart(db, user)


@router.patch("/items/{product_id}", response_model=CartResponse)
def update_item(
    product_id: uuid.UUID,
    data: CartItemUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CartResponse:
    item = _get_item_or_404(db, user, product_id)
    product = _get_for_sale_or_404(db, product_id)

    _check_stock(product, data.quantity)
    item.quantity = data.quantity
    db.commit()
    return _build_cart(db, user)


@router.delete("/items/{product_id}", response_model=CartResponse)
def remove_item(
    product_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CartResponse:
    db.delete(_get_item_or_404(db, user, product_id))
    db.commit()
    return _build_cart(db, user)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def empty_cart(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    db.execute(delete(CartItem).where(CartItem.user_id == user.id))
    db.commit()


# ---------- helpers ----------


def _find_item(db: Session, user: User, product_id: uuid.UUID) -> CartItem | None:
    # Always filter by user_id, so nobody can see or change someone else's cart
    return db.scalar(
        select(CartItem).where(CartItem.user_id == user.id, CartItem.product_id == product_id)
    )


def _get_item_or_404(db: Session, user: User, product_id: uuid.UUID) -> CartItem:
    item = _find_item(db, user, product_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This product is not in your cart")
    return item


def _get_for_sale_or_404(db: Session, product_id: uuid.UUID) -> Product:
    product = db.get(Product, product_id)
    # A hidden product can't be bought, so it looks like it doesn't exist
    if product is None or not product.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return product


def _check_stock(product: Product, quantity: int) -> None:
    if quantity <= product.stock:
        return
    if product.stock == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Sorry, this product is sold out")
    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Sorry, only {product.stock} left in stock")


def _build_cart(db: Session, user: User) -> CartResponse:
    """The cart, with all money worked out here on the server from current prices."""
    items = db.scalars(
        select(CartItem).where(CartItem.user_id == user.id).order_by(CartItem.created_at)
    )
    lines = [
        CartLine(
            product=item.product,
            quantity=item.quantity,
            line_total_cents=item.product.price_cents * item.quantity,
        )
        for item in items
        # Products the admin has hidden since are left out (they can't be bought)
        if item.product.is_active
    ]
    return CartResponse(items=lines, total_cents=sum(line.line_total_cents for line in lines))
