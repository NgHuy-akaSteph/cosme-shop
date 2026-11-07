"""Pydantic schemas cho coupon (ma giam gia)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CouponBase(BaseModel):
    """Base schema cho coupon."""

    code: str = Field(..., min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    discount_type: str = Field(..., pattern="^(percent|fixed)$")
    discount_value: int = Field(..., gt=0)
    min_order_amount: int = Field(0, ge=0)
    max_discount: int | None = Field(None, ge=0)
    max_uses: int | None = Field(None, ge=1)
    expires_at: datetime | None = None
    is_active: bool = True
    description: str | None = None


class CouponCreate(CouponBase):
    """Schema tao coupon (Admin)."""


class CouponUpdate(BaseModel):
    """Schema cap nhat coupon (Admin)."""

    discount_type: str | None = Field(None, pattern="^(percent|fixed)$")
    discount_value: int | None = Field(None, gt=0)
    min_order_amount: int | None = Field(None, ge=0)
    max_discount: int | None = Field(None, ge=0)
    max_uses: int | None = Field(None, ge=1)
    expires_at: datetime | None = None
    is_active: bool | None = None
    description: str | None = None


class CouponResponse(CouponBase):
    """Schema response coupon."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    used_count: int
    created_at: datetime
    updated_at: datetime | None = None


class CouponListResponse(BaseModel):
    data: list[CouponResponse]
    total: int
    page: int
    size: int
    message: str = "OK"


class CouponValidateRequest(BaseModel):
    """Schema validate ma giam gia o man checkout (User)."""

    code: str = Field(..., min_length=1, max_length=32)
    subtotal: int = Field(..., ge=0)


class CouponValidateResponse(BaseModel):
    """Ket qua kiem tra ma giam gia - FE hien thi preview truoc khi dat hang."""

    code: str
    discount_amount: int
    total: int
    message: str = "OK"
