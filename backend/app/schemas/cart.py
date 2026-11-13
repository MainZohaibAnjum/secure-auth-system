import uuid

from pydantic import BaseModel, Field

from app.schemas.product import MAX_STOCK, ProductResponse


class CartItemAdd(BaseModel):
    """Put a product in the cart (or add more of it)."""

    product_id: uuid.UUID
    quantity: int = Field(default=1, ge=1, le=MAX_STOCK)


class CartItemUpdate(BaseModel):
    """Set exactly how many of a product are in the cart."""

    quantity: int = Field(ge=1, le=MAX_STOCK)


class CartLine(BaseModel):
    product: ProductResponse
    quantity: int
    line_total_cents: int  # price x quantity, worked out by the server


class CartResponse(BaseModel):
    items: list[CartLine]
    total_cents: int
