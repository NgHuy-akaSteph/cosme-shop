"""Pydantic schemas cho ProductImage."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductImageBase(BaseModel):
    """Base schema cho product image."""

    public_id: str
    url: str
    secure_url: str
    alt_text: str | None = None
    width: int | None = None
    height: int | None = None
    format: str | None = None
    position: int = Field(0, ge=0)
    is_main: bool = False


class ProductImageCreate(ProductImageBase):
    """Schema tao product image (internal use)."""


class ProductImageUpdate(BaseModel):
    """Schema cap nhat product image."""

    alt_text: str | None = None
    position: int | None = Field(None, ge=0)
    is_main: bool | None = None


class ProductImageRead(ProductImageBase):
    """Schema response product image."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    created_at: datetime
    updated_at: datetime
