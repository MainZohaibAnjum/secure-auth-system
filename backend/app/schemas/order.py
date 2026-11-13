import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.order import OrderStatus


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: uuid.UUID | None  # empty if the product was deleted later
    product_name: str
    unit_price_cents: int  # the price at the moment of checkout
    quantity: int
    line_total_cents: int


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    total_cents: int
    created_at: datetime
    items: list[OrderItemResponse]


class AdminOrderResponse(OrderResponse):
    """What an admin sees: the order, plus who placed it."""

    user_email: str


class OrderStatusUpdate(BaseModel):
    """What an admin sends to move an order on, e.g. {"status": "shipped"}."""

    status: OrderStatus
