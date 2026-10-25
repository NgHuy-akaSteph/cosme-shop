"""Model luu Cloudinary public_id + URL cho moi anh san pham."""

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin


class ProductImage(Base, IdMixin, TimestampMixin):
    """Anh san pham - luu Cloudinary public_id de de quan ly tu Cloudinary dashboard."""

    __tablename__ = "product_images"

    # Foreign key (cascade delete khi xoa product)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Cloudinary fields (bat buoc)
    public_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    secure_url: Mapped[str] = mapped_column(String(500), nullable=False)

    # Metadata (optional)
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    format: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Ordering & display
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_main: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationship
    product: Mapped["Product"] = relationship(
        "Product", back_populates="images_rel"
    )

    def __repr__(self) -> str:
        return f"<ProductImage(id={self.id}, product_id={self.product_id}, public_id={self.public_id})>"
