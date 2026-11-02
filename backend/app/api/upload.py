"""Upload API endpoints - Admin only.

Quan ly upload anh san pham len Cloudinary.
"""

from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.cloudinary import build_image_urls
from app.core.config import settings
from app.db.session import get_db
from app.model.product_image import ProductImage
from app.model.user import User
from app.schemas.product_image import ProductImageRead, ProductImageReorder
from app.service import product_image_service

router = APIRouter(prefix="/api/upload", tags=["upload"])


def _serialize_image(image: ProductImage) -> dict[str, Any]:
    """
    Chuyen ProductImage ORM -> dict kem bien the URL theo kich co.

    `image_urls` khong phai cot DB - duoc sinh tu `public_id` qua Cloudinary
    transformation. Response model `ProductImageRead` co khai bao truong nay
    nhung ORM object khong tu dong dien -> can gan tay.
    """
    return {
        "id": image.id,
        "product_id": image.product_id,
        "public_id": image.public_id,
        "secure_url": image.secure_url,
        "alt_text": image.alt_text,
        "width": image.width,
        "height": image.height,
        "format": image.format,
        "position": image.position,
        "is_main": image.is_main,
        "image_urls": build_image_urls(image.public_id),
        "created_at": image.created_at,
        "updated_at": image.updated_at,
    }


# Magic bytes cho cac dinh dang anh duoc phep.
# Phai khop voi `ALLOWED_UPLOAD_FORMATS` trong app.core.cloudinary -
# neu API cho phep format ma Cloudinary chan, user se thay loi 502
# "Cloudinary that bai" thay vi thong bao ro rang.
_IMAGE_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _detect_image_type(content: bytes) -> str | None:
    """Doan content-type tu magic bytes. Tra None neu khong phai anh hop le."""
    for signature, mime in _IMAGE_SIGNATURES:
        if content.startswith(signature):
            return mime

    # WEBP: "RIFF" + 4 byte size + "WEBP"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"

    return None


def _validate_image(file: UploadFile, max_bytes: int) -> bytes:
    """
    Validate file type + size. Return content bytes.

    Kiem tra 2 lop:
    1. Content-type tu client (co the gia mao)
    2. Magic bytes cua file thuc te (khong the gia mao)

    Raises:
        HTTPException 400 neu khong hop le
    """
    if not file.content_type or file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Chi cho phep file anh (jpg, png, webp)",
                "code": "INVALID_FILE_TYPE",
            },
        )

    # Read content
    content = file.file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": f"File qua lon (max {max_bytes // (1024 * 1024)}MB)",
                "code": "FILE_TOO_LARGE",
            },
        )

    # Kiem tra magic bytes - file co that la anh hay khong
    detected_type = _detect_image_type(content)
    if detected_type is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Noi dung file khong phai la anh hop le",
                "code": "INVALID_FILE_TYPE",
            },
        )

    return content


@router.post(
    "/product-image/{product_id}",
    response_model=ProductImageRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    alt_text: str | None = Form(None),
    is_main: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> Any:
    """
    Upload anh san pham len Cloudinary.

    - **file**: File anh (jpg/png/webp, max 5MB)
    - **alt_text**: Mo ta anh (optional)
    - **is_main**: Danh dau la anh chinh (default: false)

    Returns: ProductImage object luu trong DB.
    """
    content = _validate_image(file, settings.CLOUDINARY_MAX_FILE_SIZE)

    try:
        image = await product_image_service.create_image(
            db=db,
            product_id=product_id,
            file=content,
            alt_text=alt_text,
            is_main=is_main,
            filename=file.filename,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": str(exc), "code": "NOT_FOUND"},
        )
    except HTTPException:
        raise
    except IntegrityError as exc:
        # Vi pham unique constraint (vd. public_id trung - upload trung
        # public_id) -> loi client, khong phai loi Cloudinary.
        print(f"DB integrity error on upload: {exc}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Anh da ton tai, vui long thu lai",
                "code": "DUPLICATE_IMAGE",
            },
        )
    except Exception as exc:
        print(f"Cloudinary upload failed: {exc}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Upload len Cloudinary that bai",
                "code": "CLOUDINARY_ERROR",
            },
        )

    return _serialize_image(image)


@router.get("/product-image/product/{product_id}", response_model=list[ProductImageRead])
async def list_product_images(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> Any:
    """Lay danh sach anh cua 1 san pham (sap xep theo position)."""
    images = await product_image_service.get_images_by_product(db, product_id)
    return [_serialize_image(img) for img in images]


@router.delete("/product-image/{image_id}", response_model=dict)
async def delete_product_image(
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> Any:
    """
    Xoa anh khoi Cloudinary + DB.

    Neu anh da duoc ban (co trong lich su don hang) thi asset Cloudinary
    duoc giu lai, chi go row khoi gallery.
    """
    result = await product_image_service.delete_image_by_id(db, image_id)
    if not result["deleted"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Khong tim thay anh", "code": "NOT_FOUND"},
        )

    message = (
        "Anh da duoc ban - asset duoc giu lai de bao dam lich su don hang"
        if result["asset_kept"]
        else "Xoa anh thanh cong"
    )
    return {
        "message": message,
        "image_id": image_id,
        "asset_kept": result["asset_kept"],
    }


@router.patch("/product-image/{image_id}/set-main", response_model=ProductImageRead)
async def set_main_product_image(
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> Any:
    """Set 1 anh lam main, unset cac anh khac cua cung product."""
    try:
        image = await product_image_service.set_main_image(db, image_id)
    except IntegrityError as exc:
        # Race condition: 2 request set-main chay song song -> unique index
        # `uq_product_images_one_main` reject -> bao loi conflict thay vi 500.
        print(f"Integrity error on set-main: {exc}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Anh chinh dang duoc cap nhat, vui long thu lai",
                "code": "CONFLICT",
            },
        )

    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Khong tim thay anh", "code": "NOT_FOUND"},
        )

    return _serialize_image(image)


@router.patch("/product-image/{product_id}/reorder", response_model=list[ProductImageRead])
async def reorder_product_images(
    product_id: int,
    payload: ProductImageReorder,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> Any:
    """
    Sap xep lai thu tu anh cua san pham.

    Body: {"image_ids": [3, 1, 2]} - thu tu mong muon tu truoc den sau.
    """
    try:
        images = await product_image_service.reorder_images(
            db, product_id, payload.image_ids
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(exc), "code": "VALIDATION_ERROR"},
        )

    return [_serialize_image(img) for img in images]


@router.patch("/product-image/{image_id}", response_model=ProductImageRead)
async def update_product_image(
    image_id: int,
    alt_text: str | None = Form(None),
    position: int | None = Form(None),
    is_main: bool | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> Any:
    """Cap nhat metadata anh (alt_text, position, is_main)."""
    try:
        image = await product_image_service.update_image(
            db,
            image_id=image_id,
            alt_text=alt_text,
            position=position,
            is_main=is_main,
        )
    except IntegrityError as exc:
        print(f"Integrity error on image update: {exc}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Anh chinh dang duoc cap nhat, vui long thu lai",
                "code": "CONFLICT",
            },
        )

    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Khong tim thay anh", "code": "NOT_FOUND"},
        )

    return _serialize_image(image)
