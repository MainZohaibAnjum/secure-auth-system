import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Product
from app.schemas.product import ProductResponse

# The shop window: anyone can look, no login needed
router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductResponse])
def list_products(db: Session = Depends(get_db)) -> list[Product]:
    """Every product that's for sale, newest first."""
    return list(
        db.scalars(
            select(Product).where(Product.is_active.is_(True)).order_by(Product.created_at.desc())
        )
    )


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: uuid.UUID, db: Session = Depends(get_db)) -> Product:
    product = db.get(Product, product_id)
    # A hidden product looks exactly like one that doesn't exist
    if product is None or not product.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return product
