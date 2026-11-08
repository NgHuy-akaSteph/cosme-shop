"""Pydantic schemas cho order"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


from app.core.money import MoneyDecimal

class OrderItemBase(BaseModel):
    """Base schema cho order item"""
    product_id: int
    variant_id: str | None = None
    qty: int = Field(..., gt=0, le=99)


class OrderItemResponse(BaseModel):
    """Schema response order item"""
    id: int
    product_id: int
    product_name: str
    product_price: MoneyDecimal
    product_image: str | None = None
    variant_info: dict[str, Any] | None = None
    qty: int
    subtotal: MoneyDecimal


class OrderBase(BaseModel):
    """Base schema cho order"""
    items: list[OrderItemBase]
    shipping_name: str = Field(..., min_length=2, max_length=255)
    shipping_phone: str = Field(..., pattern=r"^0\d{9,10}$")
    shipping_address: str = Field(..., min_length=5)
    payment_method: str = Field(..., pattern="^(cod|sepay)$")
    note: str | None = None
    # Ma giam gia (optional). Server tu validate + tinh tien giam.
    coupon_code: str | None = Field(None, max_length=32)


class OrderCreate(OrderBase):
    """Schema tao order"""
    pass


class OrderStatusHistoryResponse(BaseModel):
    """Schema response lich su trang thai"""
    id: int
    status: str
    note: str | None = None
    created_by: int | None = None
    created_at: datetime


class OrderResponse(BaseModel):
    """Schema response order"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    order_code: str
    status: str
    subtotal: MoneyDecimal
    discount_code: str | None = None
    discount_amount: MoneyDecimal
    total: MoneyDecimal
    payment_method: str
    payment_status: str
    paid_at: str | None = None
    transaction_id: str | None = None
    shipping_name: str
    shipping_phone: str
    shipping_address: str
    tracking_code: str | None = None
    carrier: str | None = None
    note: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    items: list[OrderItemResponse] = []
    status_history: list[OrderStatusHistoryResponse] = []


class OrderListResponse(BaseModel):
    data: list[OrderResponse]
    total: int
    page: int
    size: int
    message: str = "OK"


class OrderStatusUpdate(BaseModel):
    """Schema cap nhat trang thai order (Admin)"""
    status: str = Field(..., pattern="^(confirmed|packing|shipping|delivered|cancelled)$")
    note: str | None = None


class CheckoutResponse(BaseModel):
    """Schema response checkout"""
    order: OrderResponse
    qr_url: str | None = None  # SePay QR URL
    message: str = "Đặt hàng thành công"


class OrderCodeResponse(BaseModel):
    """Schema response ma don (SePay)"""
    order_code: str
    qr_url: str | None = None
    amount: MoneyDecimal
    message: str = "OK"
