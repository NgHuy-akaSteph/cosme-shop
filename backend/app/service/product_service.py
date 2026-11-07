"""Product service - business logic"""

import re
from decimal import Decimal

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.model.product import Product
from app.model.category import Category
from app.model.brand import Brand
from app.service import product_stock


def generate_slug(name: str) -> str:
    """Tao slug tu ten san pham."""
    # Chuyen thanh chu thuong, thay khoang trang bang dau gach ngang
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)  # Loai bo ky tu dac biet
    slug = re.sub(r'[-\s]+', '-', slug)  # Thay khoang trang = dau gach ngang
    return slug.strip('-')


# Cac field cho phep gan gia tri None khi update (xoa du lieu cu)
NULLABLE_FIELDS = {
    "description",
    "sale_price",
    "skin_types",
    "concerns",
    "key_ingredients",
    "free_from",
    "variants",
}


async def get_product_by_id(db: AsyncSession, product_id: int) -> Product | None:
    """Lay product theo ID."""
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.brand),
            selectinload(Product.images_rel),
        )
        .where(Product.id == product_id)
    )
    return result.scalar_one_or_none()


async def get_product_by_slug(db: AsyncSession, slug: str) -> Product | None:
    """Lay product theo slug."""
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.brand),
            selectinload(Product.images_rel),
        )
        .where(Product.slug == slug)
    )
    return result.scalar_one_or_none()


async def get_products(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    category_id: int | None = None,
    brand_id: int | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    skin_types: list[str] | None = None,
    concerns: list[str] | None = None,
    search: str | None = None,
    sort: str | None = None,
    is_active: bool = True,
) -> tuple[list[Product], int]:
    """
    Lay danh sach products voi filter.
    
    Returns:
        Tuple of (products, total_count)
    """
    query = select(Product).options(
        selectinload(Product.category),
        selectinload(Product.brand),
        selectinload(Product.images_rel),
    )
    
    count_query = select(func.count(Product.id))
    
    # Filter by active status
    if is_active:
        query = query.where(Product.is_active == True)
        count_query = count_query.where(Product.is_active == True)
    
    # Filter by category
    if category_id:
        query = query.where(Product.category_id == category_id)
        count_query = count_query.where(Product.category_id == category_id)
    
    # Filter by brand
    if brand_id:
        query = query.where(Product.brand_id == brand_id)
        count_query = count_query.where(Product.brand_id == brand_id)
    
    # Filter by price range
    if min_price is not None:
        effective_price = func.coalesce(Product.sale_price, Product.price)
        query = query.where(effective_price >= min_price)
        count_query = count_query.where(effective_price >= min_price)
    
    if max_price is not None:
        effective_price = func.coalesce(Product.sale_price, Product.price)
        query = query.where(effective_price <= max_price)
        count_query = count_query.where(effective_price <= max_price)
    
    # Filter by skin types (JSON contains any - OR semantics)
    if skin_types:
        cond = or_(*[Product.skin_types.contains([st]) for st in skin_types])
        query = query.where(cond)
        count_query = count_query.where(cond)

    # Filter by concerns (JSON contains any - OR semantics)
    if concerns:
        cond = or_(*[Product.concerns.contains([c]) for c in concerns])
        query = query.where(cond)
        count_query = count_query.where(cond)
    
    # Search by name
    if search:
        search_pattern = f"%{search}%"
        query = query.where(Product.name.ilike(search_pattern))
        count_query = count_query.where(Product.name.ilike(search_pattern))
    
    # Count total
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # Sort
    if sort == "price_asc":
        query = query.order_by(func.coalesce(Product.sale_price, Product.price).asc())
    elif sort == "price_desc":
        query = query.order_by(func.coalesce(Product.sale_price, Product.price).desc())
    elif sort == "newest":
        query = query.order_by(Product.created_at.desc())
    elif sort == "best_seller":
        query = query.order_by(Product.sold_count.desc())
    else:
        query = query.order_by(Product.id.desc())
    
    # Pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    products = list(result.scalars().all())
    
    return products, total


async def get_best_sellers(
    db: AsyncSession, limit: int = 10
) -> list[Product]:
    """Lay san pham ban chay nhat."""
    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.brand),
            selectinload(Product.images_rel),
        )
        .where(Product.is_active == True)
        .order_by(Product.sold_count.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_similar_products(
    db: AsyncSession, product_id: int, limit: int = 8
) -> list[Product]:
    """Lay san pham tuong tu (cung category)."""
    # Lay product hien tai de biet category
    current = await get_product_by_id(db, product_id)
    if current is None:
        return []

    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.brand),
            selectinload(Product.images_rel),
        )
        .where(
            and_(
                Product.category_id == current.category_id,
                Product.id != product_id,
                Product.is_active == True,
            )
        )
        .order_by(Product.sold_count.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def create_product(
    db: AsyncSession,
    name: str,
    price: Decimal,
    category_id: int,
    brand_id: int,
    slug: str | None = None,
    **kwargs
) -> Product:
    """Tao product moi."""
    # Tao slug neu khong cung cap
    if slug is None:
        slug = generate_slug(name)
    
    # Kiem tra slug da ton tai
    existing = await get_product_by_slug(db, slug)
    if existing:
        raise ValueError("Slug đã tồn tại")
    
    product = Product(
        name=name,
        slug=slug,
        price=price,
        category_id=category_id,
        brand_id=brand_id,
        **kwargs
    )

    # `products.stock` la gia tri dan xuat khi san pham co bien the
    # (= tong stock variants) - xem service/product_stock.py.
    product_stock.recompute_stock(product)

    db.add(product)
    await db.commit()
    await db.refresh(product)
    
    # Load relationships
    product = await get_product_by_id(db, product.id)
    
    return product


async def update_product(
    db: AsyncSession, product_id: int, **kwargs
) -> Product | None:
    """Cap nhat product."""
    product = await get_product_by_id(db, product_id)
    if product is None:
        return None
    
    # Kiem tra slug moi khong trung
    new_slug = kwargs.get("slug")
    if new_slug and new_slug != product.slug:
        existing = await get_product_by_slug(db, new_slug)
        if existing:
            raise ValueError("Slug đã tồn tại")
    
    for key, value in kwargs.items():
        if not hasattr(product, key):
            continue
        # Field nullable duoc phep gan None (vd: xoa sale_price, description...)
        if value is None and key not in NULLABLE_FIELDS:
            raise ValueError(f"Không thể đặt null cho trường bắt buộc: {key}")
        setattr(product, key, value)

    # Dong bo `stock` voi variants: khi san pham co bien the, `products.stock`
    # la gia tri DAN XUAT = tong stock variants (xem service/product_stock.py).
    # Neu admin vua them/xoa/sua bien the -> stock phai cap nhat theo.
    if "variants" in kwargs or product.variants:
        product_stock.recompute_stock(product)

    await db.commit()
    await db.refresh(product)

    return await get_product_by_id(db, product_id)


async def delete_product(db: AsyncSession, product_id: int) -> bool:
    """Xoa product (soft delete)."""
    product = await get_product_by_id(db, product_id)
    if product is None:
        return False

    product.is_active = False
    await db.commit()

    return True


async def hard_delete_product(db: AsyncSession, product_id: int) -> bool:
    """
    Xoa product that su (cascade se xoa product_images rows).
    KHONG nen goi truc tiep tu admin API - chi dung cho cleanup scripts.
    Cloudinary cleanup nen duoc goi rieng truoc khi hard delete.
    """
    # Import o day tranh circular import
    from app.service.product_image_service import cleanup_cloudinary_for_product

    product = await db.get(Product, product_id)
    if product is None:
        return False

    # 1. Cleanup Cloudinary (xoa tat ca public_id)
    await cleanup_cloudinary_for_product(db, product_id)

    # 2. Xoa product (cascade se xoa product_images rows)
    await db.delete(product)
    await db.commit()

    return True
