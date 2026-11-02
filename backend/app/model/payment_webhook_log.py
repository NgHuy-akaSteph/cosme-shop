"""Model log webhook thanh toan (chong trung, audit, doi soat)"""

from sqlalchemy import BigInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class PaymentWebhookLog(Base, IdMixin, TimestampMixin):
    """Log 1 webhook thanh toan da nhan tu gateway."""

    __tablename__ = "payment_webhook_logs"

    provider: Mapped[str] = mapped_column(String(20), default="sepay", nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(64), nullable=False)
    order_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    amount: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="received", nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
