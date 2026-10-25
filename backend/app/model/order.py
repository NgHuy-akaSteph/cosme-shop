from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin


class Order(Base, IdMixin, TimestampMixin):
    """Don hang cua user"""
    
    __tablename__ = "orders"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    # Ma don - unique
    order_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    
    # Trang thai
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    
    # Tien
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 0), default=Decimal("0"), nullable=False)
    shipping_fee: Mapped[Decimal] = mapped_column(Numeric(12, 0), default=Decimal("30000"), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 0), default=Decimal("0"), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 0), default=Decimal("0"), nullable=False)
    
    # Thanh toan
    payment_method: Mapped[str] = mapped_column(String(10), nullable=False)  # cod | sepay
    payment_status: Mapped[str] = mapped_column(String(10), default="unpaid", nullable=False)  # unpaid | paid
    paid_at: Mapped[str | None] = mapped_column(String, nullable=True)  # ISO timestamp
    transaction_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Shipping
    shipping_name: Mapped[str] = mapped_column(String(255), nullable=False)
    shipping_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    shipping_address: Mapped[str] = mapped_column(Text, nullable=False)
    tracking_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    carrier: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Ghi chu
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", backref="orders")
