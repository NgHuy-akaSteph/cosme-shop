"""Service logic cho ProductImage - quan ly Cloudinary sync."""

from typing import Any

from sqlalchemy import select, update, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.cloudinary import (
    upload_image,
    delete_image,
    build_product_folder,
)
from app.model.product import Product
from app.model.product_image import ProductImage
from app.model.order_item import OrderItem


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
    filename: str | None = None,
) -> ProductImage:
    """
    Upload anh len Cloudinary va luu vao DB.

    Args:
        db: AsyncSession
        product_id: ID product
        file: bytes hoac file-like object
        alt_text: Mo ta anh (optional)
        is_main: Danh dau la anh chinh
        filename: Ten file goc (giu extension)

    Returns:
        ProductImage vua tao
    """
    # Kiem tra product ton tai
    product = await db.get(Product, product_id)
    if product is None:
        raise ValueError(f"Product {product_id} khong ton tai")

    # Upload Cloudinary vao folder rieng cua product.
    # Day la blocking IO (HTTP request) -> chay trong threadpool de khong
    # chan event loop cua FastAPI.
    result = await run_in_threadpool(
        upload_image,
        file,
        folder=build_product_folder(product_id),
        filename=filename,
    )

    # Neu is_main=True thi bo co trang thai main cua cac anh khac TRUOC khi
    # insert row moi (row moi da co is_main=True) - neu khong, unique index
    # `uq_product_images_one_main` se bao loi khi commit.
    if is_main:
        await db.execute(
            update(ProductImage)
            .where(ProductImage.product_id == product_id)
            .values(is_main=False)
        )

    # Auto-set position = max+1. Anh moi luon duoc them vao CUOI gallery.
    existing = await get_images_by_product(db, product_id)
    position = max((img.position for img in existing), default=-1) + 1

    # Tao row moi
    image = ProductImage(
        product_id=product_id,
        public_id=result["public_id"],
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

    if is_main:
        # Anh vua upload la anh chinh -> dua no len dau gallery va danh lai
        # position cac anh khac (1..N) de giu invariant "anh main luon dau".
        await _promote_to_main(db, product_id, image.id)
        await db.commit()
    else:
        # Auto-mark first image as main neu chua co anh main nao.
        await _ensure_one_main_image(db, product_id)

    # `_ensure_one_main_image` / `_promote_to_main` co commit rieng ->
    # expire_on_commit lam cac attribute (updated_at) bi expired. Refresh lai
    # de serialize response khong trigger lazy-load IO ben ngoai async context
    # (MissingGreenlet).
    await db.refresh(image)

    return image


async def is_image_used_in_orders(
    db: AsyncSession, secure_url: str
) -> bool:
    """
    Kiem tra anh da duoc snapshot vao don hang nao chua.

    `order_items.product_image` luu URL snapshot (khong FK) nen neu xoa asset
    tren Cloudinary thi URL do se 404 vinh vien trong lich su don hang.
    """
    result = await db.execute(
        select(func.count(OrderItem.id)).where(OrderItem.product_image == secure_url)
    )
    count = result.scalar_one()
    return count > 0


async def delete_image_by_id(db: AsyncSession, image_id: int) -> dict[str, Any]:
    """
    Xoa anh: xoa tren Cloudinary truoc, sau do xoa trong DB.

    Neu anh da duoc ban (co snapshot trong `order_items`) thi KHONG xoa asset
    tren Cloudinary - chi go row khoi gallery, de lich su don hang van hien
    thi dung.

    Returns:
        Dict: {"deleted": bool, "asset_kept": bool}
        - deleted: False neu khong tim thay anh
        - asset_kept: True neu asset Cloudinary duoc giu lai (anh da ban)
    """
    image = await db.get(ProductImage, image_id)
    if image is None:
        return {"deleted": False, "asset_kept": False}

    product_id = image.product_id
    was_main = image.is_main
    secure_url = image.secure_url

    # 1. Kiem tra anh da duoc dung trong don hang chua
    used_in_orders = await is_image_used_in_orders(db, secure_url)

    # 2. Xoa tren Cloudinary (chi khi anh chua duoc ban)
    asset_kept = False
    if used_in_orders:
        asset_kept = True
        print(
            f"Keeping Cloudinary asset {image.public_id}: "
            "image is referenced in order history"
        )
    else:
        try:
            delete_image(image.public_id)
        except Exception as exc:
            print(f"Warning: Failed to delete from Cloudinary {image.public_id}: {exc}")

    # 3. Xoa trong DB
    await db.delete(image)
    await db.commit()

    # 4. Neu vua xoa anh main, set anh dau tien con lai lam main
    if was_main:
        await _ensure_one_main_image(db, product_id)

    return {"deleted": True, "asset_kept": asset_kept}


async def _promote_to_main(
    db: AsyncSession, product_id: int, image_id: int
) -> None:
    """
    Dat anh `image_id` lam anh main va dua no len dau gallery.

    Position cua cac anh khac duoc danh lai lien tuc 1..N (anh main = 0)
    de storefront hien thi anh main dau danh sach.

    Thuc hien bang 3 cau lenh trong cung 1 transaction:
    1. Reset `is_main` cua tat ca anh cua product -> false.
    2. Renumber position cua anh khac (1..N) roi dat target = 0 / main = true.

    Tach thanh nhieu lenh (thay vi 1 lenh `CASE`) de tranh unique index
    `uq_product_images_one_main` bao loi trung khi DB xu ly thu tu dong:
    - 1 lenh UPDATE set ca target=true va anh cu=false -> Postgres kiem tra
      unique theo tung dong, co the thay 2 dong cung true va bao loi du
      "duplicate key" du cau hinh cuoi cung chi co 1 anh main.
    """
    # 1. Bo co trang thai main cua tat ca anh cua product.
    #    Chay TRUOCC khi dat target de unique index khong bao loi.
    await db.execute(
        update(ProductImage)
        .where(ProductImage.product_id == product_id)
        .values(is_main=False)
    )

    # 2. Renumber position cua anh khac thanh 1..N lien tuc (ROW_NUMBER),
    #    bo qua anh target (no se nhan position 0).
    await db.execute(
        text(
            """
            WITH ordered AS (
                SELECT id,
                       ROW_NUMBER() OVER (ORDER BY position, id) AS new_position
                FROM product_images
                WHERE product_id = :product_id AND id != :image_id
            )
            UPDATE product_images pi
            SET position = ordered.new_position
            FROM ordered
            WHERE pi.id = ordered.id
            """
        ),
        {"product_id": product_id, "image_id": image_id},
    )

    # 3. Dat target: is_main = true, position = 0.
    await db.execute(
        update(ProductImage)
        .where(ProductImage.id == image_id)
        .values(is_main=True, position=0)
    )


async def set_main_image(
    db: AsyncSession, image_id: int
) -> ProductImage | None:
    """Set 1 anh lam main, unset cac anh khac."""
    target = await db.get(ProductImage, image_id)
    if target is None:
        return None

    await _promote_to_main(db, target.product_id, target.id)
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

    if is_main is True:
        # Promote thay the luon de giu invariant "anh main luon o dau gallery".
        # `position` bi bo qua trong truong hop nay vi position cua anh main
        # luon = 0.
        await _promote_to_main(db, image.product_id, image.id)
        await db.commit()
        await db.refresh(image)
        return image

    # Capture trang thai main TRUOC khi mutate de biet co can xu ly lai
    # hay khong (neu anh nay khong phai main thi bo qua hoan toan).
    was_main = image.is_main

    if position is not None:
        image.position = position

    if is_main is False and was_main:
        # Bo co trang thai main -> phai dat anh khac lam main neu con anh.
        # Chon anh tiep theo trong thu tu hien tai, BO QUA anh vua unset
        # (neu khong, `_ensure_one_main_image` se chon lai chinh anh do va
        # vo hieu hoa thay doi cua admin).
        remaining = [
            img
            for img in await get_images_by_product(db, image.product_id)
            if img.id != image.id
        ]
        if remaining:
            await _promote_to_main(db, image.product_id, remaining[0].id)
        else:
            # Anh nay la anh duy nhat cua gallery -> van phai giu lai
            # trang thai main (invariant: product co anh luon co 1 anh main).
            await _ensure_one_main_image(db, image.product_id)
        await db.commit()
        await db.refresh(image)
        return image

    if is_main is not None:
        # `is_main=False` tren anh khong phai main -> chi can persist flag.
        image.is_main = is_main

    await db.commit()
    await db.refresh(image)
    return image


async def reorder_images(
    db: AsyncSession, product_id: int, image_ids: list[int]
) -> list[ProductImage]:
    """
    Sap xep lai thu tu anh cua product theo danh sach ID client gui len.

    Args:
        db: AsyncSession
        product_id: ID product
        image_ids: Thu tu ID mong muon (anh moi nhat den cuoi)

    Returns:
        List ProductImage sau khi sap xep

    Raises:
        ValueError neu ID khong thuoc product hoac trung lap
    """
    existing = await get_images_by_product(db, product_id)
    existing_ids = {img.id for img in existing}

    # Validate: tat ca ID phai thuoc dung product
    invalid = [i for i in image_ids if i not in existing_ids]
    if invalid:
        raise ValueError(
            f"Anh khong thuoc san pham nay: {invalid}"
        )

    # Validate: khong trung lap
    if len(set(image_ids)) != len(image_ids):
        raise ValueError("Danh sach anh bi trung lap")

    # Gán lại position theo thứ tự mới
    for position, image_id in enumerate(image_ids):
        await db.execute(
            update(ProductImage)
            .where(ProductImage.id == image_id)
            .values(position=position)
        )

    await db.commit()
    return await get_images_by_product(db, product_id)


async def cleanup_cloudinary_for_product(
    db: AsyncSession, product_id: int
) -> list[str]:
    """
    Xoa tat ca anh cua product tren Cloudinary.
    Su dung truoc khi xoa product that (hard delete).

    Anh da duoc ban se duoc giu lai tren Cloudinary de lich su don hang
    khong bi hong.

    Returns:
        List public_ids da xoa
    """
    result = await db.execute(
        select(ProductImage).where(ProductImage.product_id == product_id)
    )
    images = list(result.scalars().all())

    deleted: list[str] = []
    for img in images:
        if await is_image_used_in_orders(db, img.secure_url):
            print(
                f"Keeping Cloudinary asset {img.public_id}: "
                "image is referenced in order history"
            )
            continue
        try:
            result = delete_image(img.public_id)
            if result.get("result") == "ok":
                deleted.append(img.public_id)
        except Exception as exc:
            print(f"Warning: Failed to delete from Cloudinary {img.public_id}: {exc}")

    return deleted


async def _ensure_one_main_image(
    db: AsyncSession, product_id: int
) -> None:
    """
    Dam bao luon co 1 anh main (neu co anh).

    Anh main duoc dat o `position = 0` va cac anh khac duoc danh lai
    `1..N` lien tuc, giu invariant "anh main luon o dau gallery".
    """
    result = await db.execute(
        select(ProductImage)
        .where(ProductImage.product_id == product_id)
        .order_by(ProductImage.position, ProductImage.id)
    )
    images = list(result.scalars().all())

    if not images:
        return

    main_images = [img for img in images if img.is_main]

    if len(main_images) == 0:
        # Set anh dau tien lam main
        await _promote_to_main(db, product_id, images[0].id)
        await db.commit()
    elif len(main_images) > 1:
        # Chi giu anh dau tien la main
        for img in main_images[1:]:
            img.is_main = False
        await db.commit()
