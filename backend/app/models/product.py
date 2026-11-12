import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Product(Base):
    """Something the shop sells."""

    __tablename__ = "products"
    # The database itself refuses negative prices or stock, even if the code has a bug
    __table_args__ = (
        CheckConstraint("price_cents >= 0", name="price_not_negative"),
        CheckConstraint("stock >= 0", name="stock_not_negative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")

    # Money is stored in whole cents (1999 = 19.99). Decimals like 0.1 can't be
    # stored exactly as floats, so adding them up would give wrong totals.
    price_cents: Mapped[int]
    stock: Mapped[int]
    image_url: Mapped[str | None] = mapped_column(String(500))

    # Hidden products stay in the database but don't show in the shop
    is_active: Mapped[bool] = mapped_column(default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
