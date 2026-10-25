"""Pydantic schemas cho category"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CategoryBase(BaseModel):
    """Base schema cho category"""
    name: str
    slug: str
    description: str | None = None
    image_url: str | None = None


class CategoryCreate(CategoryBase):
    """Schema tao category (Admin)"""
    pass


class CategoryUpdate(BaseModel):
    """Schema cap nhat category (Admin)"""
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    image_url: str | None = None


class CategoryResponse(CategoryBase):
    """Schema response category"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime | None = None


class CategoryListResponse(BaseModel):
    data: list[CategoryResponse]
    total: int
    page: int
    size: int
    message: str = "OK"
