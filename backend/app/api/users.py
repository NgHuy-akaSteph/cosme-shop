"""User management API endpoints (Admin)"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user, get_current_admin
from app.model.user import User
from app.service.user_service import (
    count_users,
    get_all_users,
    get_user_by_id,
    toggle_user_active,
)
from pydantic import BaseModel

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])


class UserListResponse(BaseModel):
    data: list[dict]
    total: int
    page: int
    size: int
    message: str = "OK"


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = 1,
    size: int = 20,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Lay danh sach nguoi dung (Admin).
    """
    skip = (page - 1) * size
    users = await get_all_users(db, skip=skip, limit=size)
    
    user_list = [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "phone": u.phone,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at,
        }
        for u in users
    ]
    
    return UserListResponse(
        data=user_list,
        total=await count_users(db),
        page=page,
        size=size,
    )


@router.get("/{user_id}", response_model=dict)
async def get_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Lay chi tiet nguoi dung theo ID (Admin).
    """
    user = await get_user_by_id(db, user_id)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Không tìm thấy người dùng", "code": "NOT_FOUND"},
        )
    
    return {
        "data": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "address": user.address,
            "avatar_url": user.avatar_url,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
        },
        "message": "OK",
    }


@router.patch("/{user_id}/toggle-active", response_model=dict)
async def toggle_active(
    user_id: int,
    is_active: bool,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Khoa/mo khoa tai khoan nguoi dung (Admin).
    """
    user = await toggle_user_active(db, user_id, is_active)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Không tìm thấy người dùng", "code": "NOT_FOUND"},
        )
    
    action = "Mở khóa" if is_active else "Khóa"
    
    return {
        "data": {
            "id": user.id,
            "email": user.email,
            "is_active": user.is_active,
        },
        "message": f"{action} tài khoản thành công",
    }
