"""Payment API endpoints - SePay webhook"""

import hmac
import logging
import re
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.config import settings
from app.service import order_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payment", tags=["payment"])


class SePayWebhookPayload(BaseModel):
    """SePay webhook payload."""
    content: str
    amount_in: float | None = None
    transfer_type: str | None = None
    transaction_id: str | None = None
    transaction_time: str | None = None


@router.post("/sepay-webhook")
async def sepay_webhook(
    payload: SePayWebhookPayload,
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook nhan thong bao thanh toan tu SePay.
    - Verify API key
    - Extract order code from content
    - Update payment_status = paid
    """
    # Verify API key. Chưa cấu hình key thì từ chối toàn bộ (tránh khớp chuỗi rỗng).
    expected_key = settings.SEPAY_API_KEY
    prefix = "Apikey "
    provided_key = (
        authorization[len(prefix):] if authorization and authorization.startswith(prefix) else ""
    )
    if not expected_key or not hmac.compare_digest(
        provided_key.encode(), expected_key.encode()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Unauthorized", "code": "UNAUTHORIZED"},
        )

    # Chỉ xử lý giao dịch tiền vào
    if payload.transfer_type != "in":
        return {"success": True}

    # Extract order code from content (regex: ORD followed by digits)
    match = re.search(r'ORD\d+', payload.content)
    if not match:
        return {"success": True}  # Not an order, but still success to stop retries

    order_code = match.group(0)

    try:
        order = await order_service.get_order_by_code(db, order_code)
        if order is None:
            return {"success": True}

        # Số tiền chuyển phải đủ so với tổng đơn
        if payload.amount_in is None or Decimal(str(payload.amount_in)) < order.total:
            logger.warning(
                "SePay amount mismatch for %s: got=%s expected=%s",
                order_code, payload.amount_in, order.total,
            )
            return {"success": True}

        await order_service.update_payment_status(
            db,
            order_code=order_code,
            transaction_id=payload.transaction_id,
        )
    except Exception:
        logger.exception("SePay webhook failed for order %s", order_code)
        await db.rollback()
        # Trả 500 để SePay retry thay vì mất giao dịch
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Webhook processing failed", "code": "INTERNAL_ERROR"},
        )

    return {"success": True}


@router.get("/status/{order_id}", response_model=dict)
async def get_payment_status(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Lay trang thai thanh toan cua don hang.
    """
    from app.api.orders import _order_to_dict
    
    order = await order_service.get_order_by_id(db, order_id)
    
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Không tìm thấy đơn hàng", "code": "NOT_FOUND"},
        )
    
    return {
        "data": {
            "order_code": order.order_code,
            "payment_status": order.payment_status,
            "paid_at": order.paid_at,
        },
        "message": "OK",
    }
