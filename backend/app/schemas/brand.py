"""Pydantic schemas cho brand"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BrandBase(BaseModel):
    """Base schema cho brand"""
    name: str
    slug: str
    description: str | None = None
    logo_url: str | None = None


class BrandCreate(BrandBase):
    """Schema tao brand (Admin)"""
    pass


class BrandUpdate(BaseModel):
    """Schema cap nhat brand (Admin)"""
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    logo_url: str | None = None


class BrandResponse(BrandBase):
    """Schema response brand"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime | None = None


class BrandListResponse(BaseModel):
    data: list[BrandResponse]
    total: int
    page: int
    size: int
    message: str = "OK"
