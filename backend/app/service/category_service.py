"""Category service - business logic"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.category import Category


async def get_category_by_id(db: AsyncSession, category_id: int) -> Category | None:
    """Lay category theo ID."""
    result = await db.execute(select(Category).where(Category.id == category_id))
    return result.scalar_one_or_none()


async def get_category_by_slug(db: AsyncSession, slug: str) -> Category | None:
    """Lay category theo slug."""
    result = await db.execute(select(Category).where(Category.slug == slug))
    return result.scalar_one_or_none()


async def get_all_categories(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Category]:
    """Lay danh sach tat ca categories."""
    result = await db.execute(
        select(Category).order_by(Category.name).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def get_categories_count(db: AsyncSession) -> int:
    """Dem so luong categories."""
    result = await db.execute(select(func.count(Category.id)))
    return result.scalar_one()


async def create_category(
    db: AsyncSession, name: str, slug: str, description: str | None = None, image_url: str | None = None
) -> Category:
    """Tao category moi."""
    # Kiem tra slug da ton tai
    existing = await get_category_by_slug(db, slug)
    if existing:
        raise ValueError("Slug đã tồn tại")
    
    category = Category(
        name=name,
        slug=slug,
        description=description,
        image_url=image_url,
    )
    
    db.add(category)
    await db.commit()
    await db.refresh(category)
    
    return category


async def update_category(
    db: AsyncSession, category_id: int, **kwargs
) -> Category | None:
    """Cap nhat category."""
    category = await get_category_by_id(db, category_id)
    if category is None:
        return None
    
    for key, value in kwargs.items():
        if value is not None and hasattr(category, key):
            setattr(category, key, value)
    
    await db.commit()
    await db.refresh(category)
    
    return category


async def delete_category(db: AsyncSession, category_id: int) -> bool:
    """Xoa category (soft delete - khong xu ly trong MVP)."""
    category = await get_category_by_id(db, category_id)
    if category is None:
        return False
    
    # Trong MVP, khong xoa cung - co the soft delete neu can
    await db.delete(category)
    await db.commit()
    
    return True
