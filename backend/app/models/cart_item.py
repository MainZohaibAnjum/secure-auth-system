import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.product import Product


class CartItem(Base):
    """One line in a user's cart: which product, and how many."""

    __tablename__ = "cart_items"
    __table_args__ = (
        # A product appears only once per cart; adding it again raises the quantity
        UniqueConstraint("user_id", "product_id", name="one_line_per_product"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # ondelete="CASCADE": deleting the user or the product also deletes these lines
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    quantity: Mapped[int]

    # No price is stored here: the cart always uses the product's current price
    product: Mapped[Product] = relationship(lazy="joined")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
