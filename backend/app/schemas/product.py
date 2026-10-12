"""Pydantic schemas cho product"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product_image import ProductImageRead


class VariantInfo(BaseModel):
    """Thong tin variant"""
    id: str
    name: str
    price: Decimal | None = None
    stock: int | None = None
    image_url: str | None = None


class ProductBase(BaseModel):
    """Base schema cho product"""
    name: str
    slug: str
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
    pass


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
