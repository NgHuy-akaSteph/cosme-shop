"""Brand service - business logic"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.brand import Brand


async def get_brand_by_id(db: AsyncSession, brand_id: int) -> Brand | None:
    """Lay brand theo ID."""
    result = await db.execute(select(Brand).where(Brand.id == brand_id))
    return result.scalar_one_or_none()


async def get_brand_by_slug(db: AsyncSession, slug: str) -> Brand | None:
    """Lay brand theo slug."""
    result = await db.execute(select(Brand).where(Brand.slug == slug))
    return result.scalar_one_or_none()


async def get_all_brands(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Brand]:
    """Lay danh sach tat ca brands."""
    result = await db.execute(
        select(Brand).order_by(Brand.name).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def get_brands_count(db: AsyncSession) -> int:
    """Dem so luong brands."""
    result = await db.execute(select(func.count(Brand.id)))
    return result.scalar_one()


async def create_brand(
    db: AsyncSession, name: str, slug: str, description: str | None = None, logo_url: str | None = None
) -> Brand:
    """Tao brand moi."""
    # Kiem tra slug da ton tai
    existing = await get_brand_by_slug(db, slug)
    if existing:
        raise ValueError("Slug đã tồn tại")
    
    brand = Brand(
        name=name,
        slug=slug,
        description=description,
        logo_url=logo_url,
    )
    
    db.add(brand)
    await db.commit()
    await db.refresh(brand)
    
    return brand


async def update_brand(
    db: AsyncSession, brand_id: int, **kwargs
) -> Brand | None:
    """Cap nhat brand."""
    brand = await get_brand_by_id(db, brand_id)
    if brand is None:
        return None
    
    for key, value in kwargs.items():
        if value is not None and hasattr(brand, key):
            setattr(brand, key, value)
    
    await db.commit()
    await db.refresh(brand)
    
    return brand


async def delete_brand(db: AsyncSession, brand_id: int) -> bool:
    """Xoa brand."""
    brand = await get_brand_by_id(db, brand_id)
    if brand is None:
        return False
    
    await db.delete(brand)
    await db.commit()
    
    return True
