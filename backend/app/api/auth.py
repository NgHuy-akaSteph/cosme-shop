"""Authentication API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import UserRegister, UserLogin, ChangePassword, TokenResponse, AuthResponse
from app.schemas.user import UserResponse, UserUpdate
from app.service.auth_service import register_user, authenticate_user, create_user_token
from app.service.user_service import change_user_password, update_user_profile
from app.api.deps import get_current_user
from app.model.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegister,
    db: AsyncSession = Depends(get_db),
):
    """
    Dang ky tai khoan moi.
    
    - **email**: Dia chi email (phai unique)
    - **password**: Mat khau (toi thieu 6 ky tu)
    - **full_name**: Ho va ten
    """
    try:
        user = await register_user(db, data)
        token = create_user_token(user)
        
        return AuthResponse(
            data={
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                },
                "access_token": token,
                "token_type": "bearer",
            },
            message="Đăng ký thành công",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "EMAIL_EXISTS"},
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """
    Dang nhap bang email va mat khau.
    
    - **email**: Dia chi email
    - **password**: Mat khau
    """
    user = await authenticate_user(db, data.email, data.password)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Email hoặc mật khẩu không đúng", "code": "AUTH_INVALID"},
        )
    
    token = create_user_token(user)
    
    return AuthResponse(
        data={
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
            },
            "access_token": token,
            "token_type": "bearer",
        },
        message="Đăng nhập thành công",
    )


@router.get("/me", response_model=AuthResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    Lay thong tin nguoi dung hien tai.
    Can co token xac thuc.
    """
    return AuthResponse(
        data={
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "phone": current_user.phone,
            "address": current_user.address,
            "avatar_url": current_user.avatar_url,
            "role": current_user.role,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at,
        },
        message="OK",
    )


@router.patch("/me", response_model=AuthResponse)
async def update_me(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cap nhat thong tin nguoi dung hien tai.
    Can co token xac thuc.
    """
    
    try:
        update_data = UserUpdate(**data)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Dữ liệu không hợp lệ", "code": "VALIDATION_ERROR", "errors": e.errors(include_url=False, include_context=False)},
        )
    user = await update_user_profile(db, current_user, update_data)
    
    return AuthResponse(
        data={
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "address": user.address,
            "avatar_url": user.avatar_url,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        },
        message="Cập nhật thành công",
    )


@router.post("/change-password", response_model=AuthResponse)
async def change_password(
    data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Doi mat khau.
    Can co token xac thuc.
    """
    try:
        await change_user_password(
            db, current_user, data.old_password, data.new_password
        )
        
        return AuthResponse(
            data={},
            message="Đổi mật khẩu thành công",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "VALIDATION_ERROR"},
        )
