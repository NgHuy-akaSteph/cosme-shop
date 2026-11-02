"""User service - business logic"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.model.user import User
from app.schemas.user import UserUpdate


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Lay user theo ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Lay user theo email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def update_user_profile(
    db: AsyncSession, user: User, data: UserUpdate
) -> User:
    """
    Cap nhat profile cua user.

    Args:
        db: Database session
        user: Current user
        data: Update data

    Returns:
        Updated user
    """
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return user


async def change_user_password(
    db: AsyncSession, user: User, old_password: str, new_password: str
) -> User:
    """
    Doi mat khau user.

    Args:
        db: Database session
        user: User can doi mat khau
        old_password: Mat khau cu
        new_password: Mat khau moi

    Returns:
        Updated user

    Raises:
        ValueError: Neu mat khau cu sai hoac mat khau moi giong mat khau cu
    """
    if not verify_password(old_password, user.password_hash):
        raise ValueError("Mật khẩu cũ không đúng")

    if verify_password(new_password, user.password_hash):
        raise ValueError("Mật khẩu mới không được trùng với mật khẩu cũ")

    user.password_hash = hash_password(new_password)

    await db.commit()
    await db.refresh(user)

    return user


async def get_all_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[User]:
    """Lay danh sach users (cho admin)."""
    result = await db.execute(select(User).offset(skip).limit(limit))
    return list(result.scalars().all())


async def count_users(db: AsyncSession) -> int:
    """Dem tong so user trong DB (dung cho phan trang admin)."""
    result = await db.execute(select(func.count(User.id)))
    return result.scalar_one()


async def toggle_user_active(db: AsyncSession, user_id: int, is_active: bool) -> User | None:
    """
    Khoa/mo khoa tai khoan user.

    Args:
        db: Database session
        user_id: ID cua user can khoa/mo khoa
        is_active: Trang thai moi

    Returns:
        Updated user hoac None neu khong tim thay
    """
    user = await get_user_by_id(db, user_id)
    if user is None:
        return None

    user.is_active = is_active
    await db.commit()
    await db.refresh(user)

    return user
