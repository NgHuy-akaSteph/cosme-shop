"""User service - business logic"""

from typing import Any

from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.model.user import User
from app.schemas.user import UserUpdate


def user_to_dict(user: User) -> dict[str, Any]:
    """
    Serialize user thanh cong ro (khong bao gom `password_hash`).

    Dung chung cho register / login / GET /me / PATCH /me de moi noi tra ve
    cung mot hinh dang du lieu - trong do co `phone` va `address` (thong tin
    giao hang mac dinh) ma FE can de prefill form thanh toan.
    """
    return {
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
    }


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Lay user theo ID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


def _apply_user_search(query, search: str | None):
    """
    Loc danh sach user theo tu khoa (Admin).

    Tieu chi CHINH la TEN (`full_name`); email va SDT la truong phu de admin
    tra khi khong nho ten. Khong phan biet hoa/thuong (ILIKE).
    """
    if not search:
        return query
    keyword = search.strip()
    if not keyword:
        return query
    pattern = f"%{keyword}%"
    return query.where(
        or_(
            User.full_name.ilike(pattern),
            User.email.ilike(pattern),
            User.phone.ilike(pattern),
        )
    )


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


async def get_all_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
) -> list[User]:
    """
    Lay danh sach users (cho admin).

    `search`: loc theo TEN (`full_name`) - kem email/SDT lam truong phu.
    """
    query = select(User)
    query = _apply_user_search(query, search)
    # `created_at` sinh tu now() theo transaction => can tiebreak `id` de
    # phan trang on dinh.
    query = query.order_by(User.created_at.desc(), User.id.desc())
    result = await db.execute(query.offset(skip).limit(limit))
    return list(result.scalars().all())


async def count_users(db: AsyncSession, search: str | None = None) -> int:
    """
    Dem tong so user trong DB (dung cho phan trang admin).

    Phai dung cung dieu kien loc voi `get_all_users` neu khong `total` se khong
    khop so ban ghi tra ve -> phan trang sai.
    """
    query = select(func.count(User.id))
    query = _apply_user_search(query, search)
    result = await db.execute(query)
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
