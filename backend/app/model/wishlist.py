from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin


class Wishlist(Base, IdMixin):
    """San pham yeu thich cua user"""
    
    __tablename__ = "wishlists"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)  # ISO timestamp
    
    # Unique constraint: 1 user khong the them cung 1 san pham 2 lan
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_wishlist_user_product"),
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", backref="wishlists")
    product: Mapped["Product"] = relationship("Product", backref="wishlists")
