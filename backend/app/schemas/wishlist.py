"""Pydantic schemas cho wishlist"""

from pydantic import BaseModel, ConfigDict


class WishlistItemResponse(BaseModel):
    """Schema response item trong wishlist"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    product_id: int
    created_at: str
    product: dict | None = None  # Product info


class WishlistResponse(BaseModel):
    """Schema response wishlist"""
    data: list[WishlistItemResponse]
    message: str = "OK"
