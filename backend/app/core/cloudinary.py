"""Cloudinary configuration and helper functions."""

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


def upload_image(file: Any, folder: str | None = None) -> dict[str, Any]:
    """
    Upload anh len Cloudinary.

    Args:
        file: File-like object (UploadFile.file), bytes, hoac local path
        folder: Folder tuy chinh (mac dinh: settings.CLOUDINARY_FOLDER)

    Returns:
        Dict chua: public_id, url, secure_url, width, height, format, ...
    """
    return cloudinary.uploader.upload(
        file,
        folder=folder or settings.CLOUDINARY_FOLDER,
        resource_type="image",
        overwrite=False,
        unique_filename=True,
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
