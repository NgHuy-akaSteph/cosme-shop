"""Service logic cho ProductImage - quan ly Cloudinary sync."""

from typing import Any

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cloudinary import upload_image, delete_image
from app.model.product import Product
from app.model.product_image import ProductImage


async def get_images_by_product(
    db: AsyncSession, product_id: int
) -> list[ProductImage]:
    """Lay tat ca anh cua product, sap xep theo position."""
    result = await db.execute(
        select(ProductImage)
        .where(ProductImage.product_id == product_id)
        .order_by(ProductImage.position, ProductImage.id)
    )
    return list(result.scalars().all())


async def create_image(
    db: AsyncSession,
    product_id: int,
    file: Any,
    alt_text: str | None = None,
    is_main: bool = False,
) -> ProductImage:
    """
    Upload anh len Cloudinary va luu vao DB.

    Args:
        db: AsyncSession
        product_id: ID product
        file: File-like object (UploadFile.file) hoac bytes
        alt_text: Mo ta anh (optional)
        is_main: Danh dau la anh chinh

    Returns:
        ProductImage vua tao
    """
    # Kiem tra product ton tai
    product = await db.get(Product, product_id)
    if product is None:
        raise ValueError(f"Product {product_id} khong ton tai")

    # Upload Cloudinary
    result = upload_image(file)

    # Neu is_main=True thi reset cac anh khac
    if is_main:
        await db.execute(
            update(ProductImage)
            .where(ProductImage.product_id == product_id)
            .values(is_main=False)
        )

    # Auto-set position = max+1 neu chua co anh nao
    position = 0
    if not is_main:
        existing = await get_images_by_product(db, product_id)
        if existing:
            position = max(img.position for img in existing) + 1

    # Tao row moi
    image = ProductImage(
        product_id=product_id,
        public_id=result["public_id"],
        url=result["url"],
        secure_url=result["secure_url"],
        width=result.get("width"),
        height=result.get("height"),
        format=result.get("format"),
        alt_text=alt_text,
        is_main=is_main,
        position=position,
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)

    # Auto-mark first image as main neu chua co anh main nao
    await _ensure_one_main_image(db, product_id)

    return image


async def delete_image_by_id(db: AsyncSession, image_id: int) -> bool:
    """
    Xoa anh: xoa tren Cloudinary truoc, sau do xoa trong DB.

    Returns:
        True neu xoa thanh cong, False neu khong tim thay
    """
    image = await db.get(ProductImage, image_id)
    if image is None:
        return False

    product_id = image.product_id
    was_main = image.is_main

    # 1. Xoa tren Cloudinary (khong fail neu 404)
    try:
        delete_image(image.public_id)
    except Exception as exc:
        print(f"Warning: Failed to delete from Cloudinary {image.public_id}: {exc}")

    # 2. Xoa trong DB
    await db.delete(image)
    await db.commit()

    # 3. Neu vua xoa anh main, set anh dau tien con lai lam main
    if was_main:
        await _ensure_one_main_image(db, product_id)

    return True


async def set_main_image(
    db: AsyncSession, image_id: int
) -> ProductImage | None:
    """Set 1 anh lam main, unset cac anh khac."""
    target = await db.get(ProductImage, image_id)
    if target is None:
        return None

    # Unset all khac
    await db.execute(
        update(ProductImage)
        .where(
            ProductImage.product_id == target.product_id,
            ProductImage.id != image_id,
        )
        .values(is_main=False)
    )

    # Set target
    target.is_main = True
    await db.commit()
    await db.refresh(target)

    return target


async def update_image(
    db: AsyncSession,
    image_id: int,
    alt_text: str | None = None,
    position: int | None = None,
    is_main: bool | None = None,
) -> ProductImage | None:
    """Cap nhat metadata anh (alt_text, position, is_main)."""
    image = await db.get(ProductImage, image_id)
    if image is None:
        return None

    if alt_text is not None:
        image.alt_text = alt_text
    if position is not None:
        image.position = position
    if is_main is not None:
        if is_main:
            await db.execute(
                update(ProductImage)
                .where(
                    ProductImage.product_id == image.product_id,
                    ProductImage.id != image_id,
                )
                .values(is_main=False)
            )
        image.is_main = is_main

    await db.commit()
    await db.refresh(image)
    return image


async def cleanup_cloudinary_for_product(
    db: AsyncSession, product_id: int
) -> list[str]:
    """
    Xoa tat ca anh cua product tren Cloudinary.
    Su dung truoc khi xoa product that (hard delete).

    Returns:
        List public_ids da xoa
    """
    result = await db.execute(
        select(ProductImage.public_id).where(ProductImage.product_id == product_id)
    )
    public_ids = list(result.scalars().all())

    deleted: list[str] = []
    for pid in public_ids:
        try:
            result = delete_image(pid)
            if result.get("result") == "ok":
                deleted.append(pid)
        except Exception as exc:
            print(f"Warning: Failed to delete from Cloudinary {pid}: {exc}")

    return deleted


async def _ensure_one_main_image(
    db: AsyncSession, product_id: int
) -> None:
    """Dam bao luon co 1 anh main (neu co anh)."""
    result = await db.execute(
        select(ProductImage).where(ProductImage.product_id == product_id)
    )
    images = list(result.scalars().all())

    if not images:
        return

    main_images = [img for img in images if img.is_main]

    if len(main_images) == 0:
        # Set anh dau tien lam main
        images[0].is_main = True
        await db.commit()
    elif len(main_images) > 1:
        # Chi giu anh dau tien la main
        for img in images[1:]:
            img.is_main = False
        await db.commit()
