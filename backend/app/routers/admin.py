import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_admin
from app.models import Product, User
from app.schemas.admin import AdminUserResponse
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate

# Every route in this file is admin-only: require_admin runs before each one
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

# Sending null for these is ignored: a product always needs them
_REQUIRED_FIELDS = {"name", "description", "price_cents", "stock", "is_active"}


@router.get("/users", response_model=list[AdminUserResponse])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    """Every account, newest first."""
    return list(db.scalars(select(User).order_by(User.created_at.desc())))


@router.get("/products", response_model=list[ProductResponse])
def list_all_products(db: Session = Depends(get_db)) -> list[Product]:
    """Every product, hidden ones too, newest first."""
    return list(db.scalars(select(Product).order_by(Product.created_at.desc())))


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(data: ProductCreate, db: Session = Depends(get_db)) -> Product:
    # mode="json" turns the checked image link into plain text for the database
    product = Product(**data.model_dump(mode="json"))
    db.add(product)
    db.commit()
    return product


@router.patch("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: uuid.UUID, data: ProductUpdate, db: Session = Depends(get_db)
) -> Product:
    product = _get_or_404(db, product_id)

    # Only change what was sent. Sending "image_url": null removes the image.
    for field, value in data.model_dump(mode="json", exclude_unset=True).items():
        if value is None and field in _REQUIRED_FIELDS:
            continue
        setattr(product, field, value)

    db.commit()
    return product


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    db.delete(_get_or_404(db, product_id))
    db.commit()


def _get_or_404(db: Session, product_id: uuid.UUID) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return product
