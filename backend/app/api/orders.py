"""Order API endpoints"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user
from app.model.user import User
from app.schemas.order import (
    OrderCreate, OrderResponse, OrderListResponse, OrderStatusUpdate, CheckoutResponse
)
from app.service import order_service

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _order_to_dict(order) -> dict[str, Any]:
    """Convert order model to dict."""
    return {
        "id": order.id,
        "user_id": order.user_id,
        "order_code": order.order_code,
        "status": order.status,
        "subtotal": str(order.subtotal),
        "shipping_fee": str(order.shipping_fee),
        "discount": str(order.discount),
        "total": str(order.total),
        "payment_method": order.payment_method,
        "payment_status": order.payment_status,
        "paid_at": order.paid_at,
        "transaction_id": order.transaction_id,
        "shipping_name": order.shipping_name,
        "shipping_phone": order.shipping_phone,
        "shipping_address": order.shipping_address,
        "tracking_code": order.tracking_code,
        "carrier": order.carrier,
        "note": order.note,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "product_price": str(item.product_price),
                "product_image": item.product_image,
                "variant_info": item.variant_info,
                "qty": item.qty,
                "subtotal": str(item.subtotal),
            }
            for item in order.items
        ],
        "status_history": [
            {
                "id": h.id,
                "status": h.status,
                "note": h.note,
                "created_by": h.created_by,
                "created_at": h.created_at,
            }
            for h in sorted(order.status_history, key=lambda x: x.created_at, reverse=True)
        ],
    }


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Tao don hang moi (User).
    """
    try:
        order, qr_url = await order_service.create_order(
            db,
            user_id=current_user.id,
            items=[item.model_dump() for item in data.items],
            shipping_name=data.shipping_name,
            shipping_phone=data.shipping_phone,
            shipping_address=data.shipping_address,
            payment_method=data.payment_method,
            note=data.note,
        )
        
        return {
            "data": {
                "order": _order_to_dict(order),
                "qr_url": qr_url,
            },
            "message": "Đặt hàng thành công",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "VALIDATION_ERROR"},
        )


@router.get("", response_model=OrderListResponse)
async def list_my_orders(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lay danh sach don hang cua minh (User).
    """
    skip = (page - 1) * size
    orders, total = await order_service.get_user_orders(
        db, current_user.id, skip=skip, limit=size
    )
    
    return OrderListResponse(
        data=[_order_to_dict(o) for o in orders],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{order_id}", response_model=dict)
async def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lay chi tiet don hang (User - chi don cua minh).
    """
    order = await order_service.get_order_by_id(db, order_id)
    
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Không tìm thấy đơn hàng", "code": "NOT_FOUND"},
        )
    
    # User chi xem duoc don cua minh
    if order.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Không có quyền xem đơn này", "code": "FORBIDDEN"},
        )
    
    return {
        "data": _order_to_dict(order),
        "message": "OK",
    }


@router.post("/{order_id}/cancel", response_model=dict)
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Huy don hang (User).
    Chi huu khi trang thai la pending hoac confirmed.
    """
    try:
        order = await order_service.cancel_order(
            db, order_id, current_user.id
        )
        
        if order is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"message": "Không tìm thấy đơn hàng", "code": "NOT_FOUND"},
            )
        
        return {
            "data": _order_to_dict(order),
            "message": "Hủy đơn hàng thành công",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(e), "code": "INVALID_STATUS_TRANSITION"},
        )
