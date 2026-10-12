from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin


class Product(Base, IdMixin, TimestampMixin):
    """San pham - bang phuc tap nhat voi nhieu JSON columns"""

    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Gia
    price: Mapped[Decimal] = mapped_column(Numeric(12, 0), nullable=False)
    sale_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 0), nullable=True)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Quan he
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id"), nullable=False)

    # Metadata cho filter (JSONB @> contains)
    skin_types: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)  # oily, dry, combination, sensitive, normal
    concerns: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)  # acne, dark_spots, wrinkles, etc.
    key_ingredients: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    free_from: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)  # alcohol, fragrance, etc.

    # Variants (JSONB)
    variants: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)

    # Stats
    sold_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rating_avg: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0"), nullable=False)
    rating_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Soft delete
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    category: Mapped["Category"] = relationship("Category", backref="products")
    brand: Mapped["Brand"] = relationship("Brand", backref="products")
    # Quan he den ProductImage (cascade delete-orphan khi xoa product)
    images_rel: Mapped[list["ProductImage"]] = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.position",
        passive_deletes=True,
    )
