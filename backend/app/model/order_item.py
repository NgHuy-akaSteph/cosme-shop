from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin


class OrderItem(Base, IdMixin):
    """Dong chi tiet don hang - luu snapshot tai thoi diem mua"""
    
    __tablename__ = "order_items"

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    
    # Snapshot thong tin san pham tai thoi diem mua
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_price: Mapped[Decimal] = mapped_column(Numeric(12, 0), nullable=False)
    product_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    variant_info: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)  # {"id": "v1", "name": "Do Ruby"}
    
    qty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 0), nullable=False)
    
    # Relationships
    order: Mapped["Order"] = relationship("Order", backref="items")
    product: Mapped["Product"] = relationship("Product", backref="order_items")
