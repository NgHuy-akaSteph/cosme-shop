"""Pydantic schemas cho product"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.schemas.product_image import ProductImageRead


class VariantInfo(BaseModel):
    """Thong tin variant (dung de validate input tu admin)."""

    id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    price: Decimal | None = Field(None, ge=0)
    stock: int | None = Field(None, ge=0)
    image_url: str | None = None


def _normalize_variants(value: Any) -> list[dict[str, Any]] | None:
    """
    Validate + chuan hoa danh sach variants thanh dict JSON-safe.

    - Moi bien the phai co `id` va `name` khong rong.
    - `id` phai duy nhat trong 1 san pham (cart key = product_id + variant_id).
    - `price` >= 0, `stock` >= 0. `stock` null -> 0 (tranh `None < qty` khi order).
    - `price` null -> giu null (FE fallback ve `product.price`).

    Raises:
        ValueError: Neu cau truc variants khong hop le.
    """
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("Variants phải là danh sách")

    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for raw in value:
        if not isinstance(raw, dict):
            raise ValueError("Mỗi biến thể phải là một object")

        try:
            variant = VariantInfo.model_validate(raw)
        except ValidationError as exc:
            first = exc.errors()[0]
            field = ".".join(str(p) for p in first["loc"])
            raise ValueError(f"Biến thể không hợp lệ ({field}): {first['msg']}")

        if variant.id in seen_ids:
            raise ValueError(f"ID biến thể bị trùng: {variant.id}")
        seen_ids.add(variant.id)

        normalized.append(
            {
                "id": variant.id,
                "name": variant.name,
                "price": float(variant.price) if variant.price is not None else None,
                "stock": variant.stock if variant.stock is not None else 0,
                "image_url": variant.image_url,
            }
        )

    return normalized


class ProductBase(BaseModel):
    """Base schema cho product"""

    name: str
    slug: str | None = None
    description: str | None = None
    price: Decimal
    sale_price: Decimal | None = None
    stock: int = 0
    category_id: int
    brand_id: int
    skin_types: list[str] | None = None
    concerns: list[str] | None = None
    key_ingredients: list[str] | None = None
    free_from: list[str] | None = None
    variants: list[dict[str, Any]] | None = None
    is_active: bool = True


class ProductCreate(ProductBase):
    """Schema tao product (Admin)"""

    @field_validator("variants", mode="before")
    @classmethod
    def _check_variants(cls, value: Any) -> list[dict[str, Any]] | None:
        return _normalize_variants(value)


class ProductUpdate(BaseModel):
    """Schema cap nhat product (Admin)"""
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    price: Decimal | None = None
    sale_price: Decimal | None = None
    stock: int | None = None
    category_id: int | None = None
    brand_id: int | None = None
    skin_types: list[str] | None = None
    concerns: list[str] | None = None
    key_ingredients: list[str] | None = None
    free_from: list[str] | None = None
    variants: list[dict[str, Any]] | None = None
    is_active: bool | None = None

    @field_validator("variants", mode="before")
    @classmethod
    def _check_variants(cls, value: Any) -> list[dict[str, Any]] | None:
        return _normalize_variants(value)


class ProductResponse(ProductBase):
    """Schema response product (public)"""
    model_config = ConfigDict(from_attributes=True, extra="allow")

    id: int
    sold_count: int
    rating_avg: Decimal
    rating_count: int
    created_at: datetime
    updated_at: datetime | None = None

    # Include category and brand info
    category: dict | None = None
    brand: dict | None = None
    # Danh sach anh san pham (Cloudinary public_id + URL)
    images: list[ProductImageRead] = []


class ProductListResponse(BaseModel):
    data: list[ProductResponse]
    total: int
    page: int
    size: int
    message: str = "OK"


class ProductFilter(BaseModel):
    """Schema filter product"""
    category_id: int | None = None
    brand_id: int | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    skin_types: list[str] | None = None
    concerns: list[str] | None = None
    search: str | None = None
    sort: str | None = None  # price_asc, price_desc, newest, best_seller
    page: int = 1
    size: int = 20
