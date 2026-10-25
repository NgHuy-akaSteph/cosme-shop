"""Wishlist service - business logic"""

from datetime import datetime, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.model.wishlist import Wishlist
from app.model.product import Product


async def get_user_wishlist(
    db: AsyncSession,
    user_id: int,
) -> list[Wishlist]:
    """Lay danh sach san pham yeu thich cua user."""
    result = await db.execute(
        select(Wishlist)
        .options(
            selectinload(Wishlist.product).selectinload(Product.images_rel)
        )
        .where(Wishlist.user_id == user_id)
        .order_by(Wishlist.created_at.desc())
    )
    return list(result.scalars().all())


async def add_to_wishlist(
    db: AsyncSession,
    user_id: int,
    product_id: int,
) -> Wishlist:
    """Them san pham vao wishlist."""
    # Kiem tra san pham ton tai
    product = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = product.scalar_one_or_none()
    
    if product is None:
        raise ValueError("Sản phẩm không tồn tại")
    
    # Kiem tra da co trong wishlist
    existing = await db.execute(
        select(Wishlist).where(
            Wishlist.user_id == user_id,
            Wishlist.product_id == product_id
        )
    )
    existing = existing.scalar_one_or_none()
    
    if existing:
        raise ValueError("Sản phẩm đã có trong wishlist")
    
    # Tao wishlist item
    wishlist = Wishlist(
        user_id=user_id,
        product_id=product_id,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    
    db.add(wishlist)
    await db.commit()
    await db.refresh(wishlist)
    
    # Load product
    result = await db.execute(
        select(Wishlist)
        .options(selectinload(Wishlist.product))
        .where(Wishlist.id == wishlist.id)
    )
    
    return result.scalar_one()


async def remove_from_wishlist(
    db: AsyncSession,
    user_id: int,
    product_id: int,
) -> bool:
    """Xoa san pham khoi wishlist."""
    result = await db.execute(
        delete(Wishlist).where(
            Wishlist.user_id == user_id,
            Wishlist.product_id == product_id
        )
    )
    await db.commit()
    
    return result.rowcount > 0


async def is_in_wishlist(
    db: AsyncSession,
    user_id: int,
    product_id: int,
) -> bool:
    """Kiem tra san pham co trong wishlist khong."""
    result = await db.execute(
        select(Wishlist).where(
            Wishlist.user_id == user_id,
            Wishlist.product_id == product_id
        )
    )
    return result.scalar_one_or_none() is not None
