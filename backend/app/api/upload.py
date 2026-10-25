"""Upload API endpoints - Admin only.

Quan ly upload anh san pham len Cloudinary.
"""

from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.cloudinary import delete_image as cloudinary_delete
from app.core.config import settings
from app.db.session import get_db
from app.model.user import User
from app.schemas.product_image import ProductImageRead
from app.service import product_image_service

router = APIRouter(prefix="/api/upload", tags=["upload"])


def _validate_image(file: UploadFile, max_bytes: int) -> bytes:
    """
    Validate file type + size. Return content bytes.

    Raises:
        HTTPException 400 neu khong hop le
    """
    if not file.content_type or not file.content_type.startswith("image/"):
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
            file=content,  # pass bytes
            alt_text=alt_text,
            is_main=is_main,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": str(exc), "code": "NOT_FOUND"},
        )
    except Exception as exc:
        print(f"Cloudinary upload failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": "Upload len Cloudinary that bai",
                "code": "CLOUDINARY_ERROR",
            },
        )

    return image


@router.delete("/product-image/{image_id}", response_model=dict)
async def delete_product_image(
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> Any:
    """Xoa anh khoi Cloudinary + DB."""
    deleted = await product_image_service.delete_image_by_id(db, image_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Khong tim thay anh", "code": "NOT_FOUND"},
        )

    return {"message": "Xoa anh thanh cong", "image_id": image_id}


@router.patch("/product-image/{image_id}/set-main", response_model=ProductImageRead)
async def set_main_product_image(
    image_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> Any:
    """Set 1 anh lam main, unset cac anh khac cua cung product."""
    image = await product_image_service.set_main_image(db, image_id)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Khong tim thay anh", "code": "NOT_FOUND"},
        )

    return image


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
    image = await product_image_service.update_image(
        db=db,
        image_id=image_id,
        alt_text=alt_text,
        position=position,
        is_main=is_main,
    )
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Khong tim thay anh", "code": "NOT_FOUND"},
        )

    return image
