"""Pydantic schemas cho authentication"""

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """Schema cho dang ky"""
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=1, max_length=255)


class UserLogin(BaseModel):
    """Schema cho dang nhap"""
    email: EmailStr
    password: str


class ChangePassword(BaseModel):
    """Schema doi mat khau"""
    old_password: str
    new_password: str = Field(..., min_length=6)


class TokenResponse(BaseModel):
    """Response khi dang nhap thanh cong"""
    access_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    """Response chua token + user info"""
    data: dict
    message: str = "OK"
