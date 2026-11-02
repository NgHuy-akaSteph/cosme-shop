"""Admin API endpoints - quan ly don hang"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.model.user import User
from app.schemas.order import OrderListResponse, OrderStatusUpdate
from app.service import order_service

router = APIRouter(prefix="/api/admin/orders", tags=["admin-orders"])


@router.get("", response_model=OrderListResponse)
async def list_all_orders(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    user_id: int | None = None,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Lay danh sach tat ca don hang (Admin).
    """
    skip = (page - 1) * size
    orders, total = await order_service.get_all_orders(
        db, skip=skip, limit=size, status=status_filter, user_id=user_id
    )
    
    return OrderListResponse(
        data=[order_service.order_to_dict(o) for o in orders],
        total=total,
        page=page,
        size=size,
    )


@router.patch("/{order_id}/status", response_model=dict)
async def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Cap nhat trang thai don hang (Admin).
    """
    try:
        order = await order_service.update_order_status(
            db,
            order_id=order_id,
            new_status=data.status,
            note=data.note,
            updated_by=current_admin.id,
        )
        
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Không tìm thấy đơn hàng", "code": "NOT_FOUND"},
            )
        
        return {
            "data": order_service.order_to_dict(order),
            "message": "Cập nhật trạng thái thành công",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "INVALID_STATUS_TRANSITION"},
        )
