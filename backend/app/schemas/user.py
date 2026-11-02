"""Pydantic schemas cho user"""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Base schema cho user"""
    email: EmailStr
    full_name: str
    phone: str | None = None
    address: str | None = None
    avatar_url: str | None = None
    role: str = "user"
    is_active: bool = True


class UserCreate(UserBase):
    """Schema tao user (internal)"""
    password_hash: str


class UserUpdate(BaseModel):
    """Schema cap nhat user profile"""
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = None
    phone: str | None = None
    address: str | None = None
    avatar_url: str | None = None


class UserResponse(UserBase):
    """Schema tra ve user info (khong co password)"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: str
    updated_at: str | None = None


class UserInDB(UserResponse):
    """Schema user trong DB (co password_hash)"""
    password_hash: str
