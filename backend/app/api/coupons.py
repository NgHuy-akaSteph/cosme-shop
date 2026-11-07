"""Coupon API endpoints.

- `/api/coupons/validate` : User - kiem tra ma + preview so tien giam o man checkout.
- `/api/admin/coupons`   : Admin - CRUD ma giam gia.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user
from app.db.session import get_db
from app.model.user import User
from app.schemas.coupon import (
    CouponCreate,
    CouponListResponse,
    CouponResponse,
    CouponUpdate,
    CouponValidateRequest,
)
from app.service import discount_service

router = APIRouter(prefix="/api/coupons", tags=["coupons"])


@router.post("/validate", response_model=dict)
async def validate_coupon(
    data: CouponValidateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Kiem tra ma giam gia va tinh so tien giam (User).

    Chi de xem preview - khong ghi DB, khong tien luot dung.
    Server van validate lai khi tao don (nguon su that la `create_order`).
    """
    from decimal import Decimal

    coupon, discount_amount, message = await discount_service.validate_coupon(
        db, data.code, Decimal(data.subtotal)
    )

    if coupon is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": message, "code": "INVALID_COUPON"},
        )

    total = Decimal(data.subtotal) - discount_amount

    return {
        "data": {
            "code": coupon.code,
            "discount_amount": int(discount_amount),
            "total": int(total),
        },
        "message": "Áp dụng thành công",
    }


# --- Admin CRUD ---

admin_router = APIRouter(prefix="/api/admin/coupons", tags=["admin-coupons"])


@admin_router.get("", response_model=CouponListResponse)
async def list_coupons(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    is_active: bool | None = Query(None),
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lay danh sach ma giam gia (Admin)."""
    skip = (page - 1) * size
    coupons = await discount_service.get_all_coupons(
        db, skip=skip, limit=size, is_active=is_active
    )
    total = await discount_service.get_coupons_count(db, is_active=is_active)

    return CouponListResponse(
        data=[CouponResponse.model_validate(c) for c in coupons],
        total=total,
        page=page,
        size=size,
    )


@admin_router.get("/{coupon_id}", response_model=dict)
async def get_coupon(
    coupon_id: int,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lay chi tiet ma giam gia (Admin)."""
    coupon = await discount_service.get_coupon_by_id(db, coupon_id)

    if coupon is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Không tìm thấy mã giảm giá", "code": "NOT_FOUND"},
        )

    return {
        "data": CouponResponse.model_validate(coupon),
        "message": "OK",
    }


@admin_router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_coupon(
    data: CouponCreate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Tao ma giam gia moi (Admin)."""
    try:
        coupon = await discount_service.create_coupon(db, **data.model_dump())
        return {
            "data": CouponResponse.model_validate(coupon),
            "message": "Tạo mã giảm giá thành công",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "VALIDATION_ERROR"},
        )


@admin_router.patch("/{coupon_id}", response_model=dict)
async def update_coupon(
    coupon_id: int,
    data: CouponUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Cap nhat ma giam gia (Admin)."""
    try:
        coupon = await discount_service.update_coupon(
            db, coupon_id, **data.model_dump(exclude_unset=True)
        )

        if coupon is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Không tìm thấy mã giảm giá", "code": "NOT_FOUND"},
            )

        return {
            "data": CouponResponse.model_validate(coupon),
            "message": "Cập nhật thành công",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "VALIDATION_ERROR"},
        )


@admin_router.delete("/{coupon_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_coupon(
    coupon_id: int,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Xoa ma giam gia (Admin)."""
    success = await discount_service.delete_coupon(db, coupon_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Không tìm thấy mã giảm giá", "code": "NOT_FOUND"},
        )
