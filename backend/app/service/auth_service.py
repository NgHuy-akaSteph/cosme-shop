"""Authentication service - business logic"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, create_access_token
from app.model.user import User
from app.schemas.auth import UserRegister


async def register_user(db: AsyncSession, data: UserRegister) -> User:
    """
    Dang ky tai khoan moi.
    
    Args:
        db: Database session
        data: User registration data
    
    Returns:
        Created user object
    
    Raises:
        ValueError: Neu email da ton tai
    """
    # Kiem tra email da ton tai
    result = await db.execute(select(User).where(User.email == data.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise ValueError("Email đã được sử dụng")
    
    # Tao user moi
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        role="user",
        is_active=True,
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """
    Xac thuc user bang email va password.
    
    Args:
        db: Database session
        email: User email
        password: Plain password
    
    Returns:
        User object if authentication successful, None otherwise
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if user is None:
        return None
    
    if not verify_password(password, user.password_hash):
        return None
    
    if not user.is_active:
        return None
    
    return user


def create_user_token(user: User) -> str:
    """
    Tao JWT token cho user.
    
    Args:
        user: User object
    
    Returns:
        JWT token string
    """
    return create_access_token(data={"sub": str(user.id), "role": user.role})
