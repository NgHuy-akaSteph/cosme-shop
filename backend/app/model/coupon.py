"""Model ma giam gia (coupon).

Thiet ke giam nhip: chi 1 bang nay la du. Khong co bang coupon_usages,
khong co campaign/tier/rule engine.

Snapshot: khi tao don, `discount_code` + `discount_amount` duoc ghi vao
`orders` => admin sua/xoa coupon sau do khong lam thay doi lich su don cu.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class Coupon(Base, IdMixin, TimestampMixin):
    """Ma giam gia - percent (%) hoac fixed (so tien VND)."""

    __tablename__ = "coupons"

    # Ma giam gia, khong phan biet hoa/thuong. VD: "WELCOME10"
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)

    # "percent" | "fixed"
    discount_type: Mapped[str] = mapped_column(String(10), default="percent", nullable=False)

    # percent -> 10 (=10%), fixed -> 50000 (=50.000d)
    discount_value: Mapped[int] = mapped_column(Integer, nullable=False)

    # Don toi thieu de dung ma (0 = khong gioi han)
    min_order_amount: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Tran giam toi da cho percent (NULL = khong gioi han)
    max_discount: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # So lan toi da duoc dung (NULL = khong gioi han)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # So lan da dung. Cap nhat bang atomic UPDATE (xem discount_service)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Thoi han (NULL = khong het han)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
