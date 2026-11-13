import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import User


class OrderStatus(str, enum.Enum):
    """Where an order is. Payment is pretend for now, so every new order starts as paid."""

    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


# The only moves allowed. An order only ever goes forward:
#   paid -> shipped -> delivered,   or   paid -> cancelled
# Delivered and cancelled are final: nothing can come after them.
NEXT_STATUSES: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PAID: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


class Order(Base):
    """One finished checkout: what a user bought, and what they paid."""

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("total_cents >= 0", name="total_not_negative"),
        # The database itself refuses any status that isn't one of ours
        CheckConstraint(
            "status IN ('paid', 'shipped', 'delivered', 'cancelled')", name="status_known"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    total_cents: Mapped[int]

    user: Mapped[User] = relationship(lazy="joined")  # who placed it (for the admin list)
    items: Mapped[list["OrderItem"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan", order_by="OrderItem.product_name"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    @property
    def user_email(self) -> str:
        return self.user.email


class OrderItem(Base):
    """One line of an order.

    The name and price are COPIED from the product at checkout time. An order is a
    record of what really happened, so it must not change when the admin later edits
    the price, renames the product, or deletes it.
    """

    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="order_quantity_positive"),
        CheckConstraint("unit_price_cents >= 0", name="unit_price_not_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    # If the admin deletes the product, the order line stays and this becomes empty
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL")
    )
    product_name: Mapped[str] = mapped_column(String(200))
    unit_price_cents: Mapped[int]
    quantity: Mapped[int]

    @property
    def line_total_cents(self) -> int:
        return self.unit_price_cents * self.quantity
