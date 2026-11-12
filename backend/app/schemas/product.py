import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

# Upper limits stop silly values (and numbers too big for the database)
MAX_PRICE_CENTS = 100_000_000  # 1,000,000.00
MAX_STOCK = 1_000_000


class ProductCreate(BaseModel):
    """What an admin sends to add a product."""

    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    price_cents: int = Field(ge=0, le=MAX_PRICE_CENTS)
    stock: int = Field(ge=0, le=MAX_STOCK)
    # Only http(s) links, so nobody can sneak in a "javascript:" link
    image_url: HttpUrl | None = Field(default=None, max_length=500)
    is_active: bool = True


class ProductUpdate(BaseModel):
    """What an admin sends to change a product. Only the fields that are sent change."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    price_cents: int | None = Field(default=None, ge=0, le=MAX_PRICE_CENTS)
    stock: int | None = Field(default=None, ge=0, le=MAX_STOCK)
    image_url: HttpUrl | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    price_cents: int
    stock: int
    image_url: str | None
    is_active: bool
    created_at: datetime
