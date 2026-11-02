"""Cloudinary configuration and helper functions."""

import io
from typing import Any

import cloudinary
import cloudinary.api
import cloudinary.uploader

from app.core.config import settings

# Configure Cloudinary SDK (chay 1 lan khi import module)
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,  # Tra ve https URLs
)

# Cac dinh dang an duoc phep upload
ALLOWED_UPLOAD_FORMATS = ["jpg", "jpeg", "png", "webp"]


def build_product_folder(product_id: int) -> str:
    """
    Folder Cloudinary cho anh cua 1 product (de quan ly tren dashboard).

    `CLOUDINARY_FOLDER` la folder goc (VD "cosme-shop"). Folder con
    "products/{id}" duoc them o day de moi san pham mot folder rieng.
    """
    return f"{settings.CLOUDINARY_FOLDER}/products/{product_id}"


def _normalize_file(file: Any, filename: str | None = None) -> Any:
    """
    Chuan hoa input thanh file-like object co ten dung dinh dang.

    Cloudinary SDK (`utils.handle_file_parameter`) chi doc gia ten file tu
    `file.name` hoac `options['filename']`. Neu truyen raw `bytes`, SDK roi
    vao nhanh `else` va gan ten `"file"` (khong co extension) -> Cloudinary
    phai doan format va upload hay fail.

    Args:
        file: bytes | BinaryIO | str (duong dan)
        filename: Ten file goc (giu extension)

    Returns:
        File-like object san de upload.
    """
    if isinstance(file, bytes):
        buffer = io.BytesIO(file)
        buffer.name = filename or "upload"
        return buffer

    if isinstance(file, (io.BufferedReader, io.BytesIO)) and filename:
        # File-like san co san -> gan lai ten de giu extension
        try:
            file.name = filename
        except AttributeError:
            pass

    return file


def upload_image(
    file: Any,
    folder: str,
    filename: str | None = None,
) -> dict[str, Any]:
    """
    Upload anh len Cloudinary.

    Args:
        file: bytes, file-like object, hoac local path
        folder: Folder dich (bat buoc). Dung `build_product_folder(product_id)`
            cho anh san pham de moi san pham co folder rieng.
        filename: Ten file goc, giu extension de Cloudinary nhan dinh format

    Returns:
        Dict chua: public_id, url, secure_url, width, height, format, ...
    """
    return cloudinary.uploader.upload(
        _normalize_file(file, filename),
        folder=folder,
        resource_type="image",
        overwrite=False,
        unique_filename=True,
        allowed_formats=ALLOWED_UPLOAD_FORMATS,
    )


def delete_image(public_id: str) -> dict[str, Any]:
    """
    Xoa anh tren Cloudinary bang public_id.

    Returns:
        Dict voi key "result": "ok" | "not found"
    """
    return cloudinary.uploader.destroy(public_id, invalidate=True)


def get_optimized_url(
    public_id: str,
    width: int = 800,
    height: int = 800,
    crop: str = "fill",
) -> str:
    """
    Generate URL anh da duoc toi uu (WebP auto, quality auto, resize).

    Args:
        public_id: Cloudinary public_id
        width: Chieu rong (px)
        height: Chieu cao (px)
        crop: Che do crop (fill, fit, scale, ...)

    Returns:
        URL dang https voi transformations
    """
    return cloudinary.CloudinaryImage(public_id).build_url(
        width=width,
        height=height,
        crop=crop,
        quality="auto",
        fetch_format="auto",
        secure=True,
    )


def build_card_url(public_id: str) -> str:
    """URL anh cho card san pham (vuong 600x600, fill de khong meo)."""
    return get_optimized_url(public_id, width=600, height=600, crop="fill")


def build_detail_url(public_id: str) -> str:
    """URL anh lon cho trang chi tiet (1200x840, limit de khong cat mat hinh)."""
    return get_optimized_url(public_id, width=1200, height=840, crop="limit")


def build_thumb_url(public_id: str) -> str:
    """URL thumbnail nho (160x160) cho gio hang / wishlist."""
    return get_optimized_url(public_id, width=160, height=160, crop="fill")


def build_image_urls(public_id: str) -> dict[str, str]:
    """
    Bundle cac bien the URL theo kich co hien thi tren storefront.

    Chi can `public_id` de sinh ra tat ca bien the - khong can luu nhieu URL
    trong DB (tranh du lieu stale).
    """
    return {
        "card": build_card_url(public_id),
        "detail": build_detail_url(public_id),
        "thumb": build_thumb_url(public_id),
    }
