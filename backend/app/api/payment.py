"""Payment API endpoints - SePay webhook + doi soat thanh toan"""

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.model.payment_webhook_log import PaymentWebhookLog
from app.model.user import User
from app.payment import get_provider
from app.payment.transaction_key import build_transaction_key
from app.service import order_service, payment_reconcile_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payment", tags=["payment"])

PROVIDER_NAME = "sepay"


def _normalize_account(account: str | None) -> str:
    """
    Chuẩn hoá số tài khoản để so sánh.

    Ngân hàng có thể gửi `1` thay vì `0000000001` ⇒ bỏ số 0 đầu trước khi so.
    """
    value = (account or "").strip()
    if not value:
        return ""
    return value.lstrip("0") or "0"


async def _record_webhook(
    db: AsyncSession,
    provider: str,
    transaction_id: str,
    order_code: str | None,
    amount: int | None,
    payload: dict,
    status: str,
    error: str | None = None,
) -> PaymentWebhookLog | None:
    """
    Ghi log webhook.

    Returns:
        PaymentWebhookLog neu la giao dich moi, None neu da xu ly giao dich nay roi (trung).
    """
    existing = await db.execute(
        select(PaymentWebhookLog).where(
            PaymentWebhookLog.provider == provider,
            PaymentWebhookLog.transaction_id == transaction_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return None

    log_row = PaymentWebhookLog(
        provider=provider,
        transaction_id=transaction_id,
        order_code=order_code,
        amount=amount,
        payload=payload,
        status=status,
        error=error,
    )
    db.add(log_row)
    await db.flush()
    return log_row


def _mark_webhook_status(
    log_row: PaymentWebhookLog | None, status: str, error: str | None = None
) -> None:
    """Cap nhat trang thai ban ghi webhook da tao."""
    if log_row is None:
        return
    log_row.status = status
    if error:
        log_row.error = error


@router.post("/sepay-webhook")
async def sepay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook nhan thong bao thanh toan tu SePay.

    - Doc raw body de xac thuc HMAC-SHA256
    - Verify chu ky / API key
    - Ghi log webhook (chong trung o muc DB)
    - Trich ma don, cap nhat payment_status = paid
    """
    raw_body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}

    provider = get_provider(PROVIDER_NAME)
    ok, payload_or_error = provider.verify_webhook(raw_body, headers)

    if not ok:
        logger.warning("SePay webhook: xac thuc that bai (%s)", payload_or_error)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Unauthorized", "code": "UNAUTHORIZED"},
        )

    payload = payload_or_error
    raw_payload: dict[str, Any] = json.loads(raw_body or b"{}")
    # Khoá chống trùng = `referenceCode` (mã tham chiếu từ ngân hàng) vì nó
    # **ổn định giữa webhook và API v2** (2 nguồn dùng `id` khác nhau cho
    # cùng 1 giao dịch). Xem `app.payment.transaction_key`.
    transaction_id = build_transaction_key(
        reference_code=payload.reference_code,
        transaction_id=payload.transaction_id,
    )

    logger.info(
        "SePay webhook: tx=%s type=%s amount=%s gateway=%s",
        transaction_id,
        payload.transfer_type,
        payload.amount_in,
        payload.gateway,
    )

    # Chi xu ly tien vao
    if payload.transfer_type != "in":
        await _record_webhook(
            db, PROVIDER_NAME, transaction_id, None, payload.amount_in, raw_payload, "ignored"
        )
        await db.commit()
        return {"success": True}

    # Giao dịch đến từ tài khoản khác => KHÔNG đánh paid cho đơn của shop.
    # So sánh theo số (bỏ số 0 đầu) vì ngân hàng có thể gửi `1` thay vì `0000000001`.
    expected_account = _normalize_account(settings.SEPAY_BANK_ACCOUNT)
    received_account = _normalize_account(payload.account_number)
    if expected_account and received_account and received_account != expected_account:
        logger.warning(
            "SePay: giao dich den tu tai khoan khong mong doi (nhan=%s, can=%s), bo qua.",
            received_account,
            expected_account,
        )
        await _record_webhook(
            db,
            PROVIDER_NAME,
            transaction_id,
            None,
            payload.amount_in,
            raw_payload,
            "wrong_account",
        )
        await db.commit()
        return {"success": True}

    order_code = provider.extract_order_code(payload)
    if not order_code:
        # Giao dich khong phai cua shop -> ghi log, tra success de SePay khong retry
        await _record_webhook(
            db,
            PROVIDER_NAME,
            transaction_id,
            None,
            payload.amount_in,
            raw_payload,
            "unmatched",
        )
        await db.commit()
        return {"success": True}

    try:
        log_row = await _record_webhook(
            db,
            PROVIDER_NAME,
            transaction_id,
            order_code,
            payload.amount_in,
            raw_payload,
            "received",
        )
        if log_row is None:
            logger.info(
                "SePay: giao dich %s da xu ly truoc, bo qua (idempotent).", transaction_id
            )
            await db.commit()
            return {"success": True}

        order = await order_service.get_order_by_code(db, order_code)
        if order is None:
            _mark_webhook_status(log_row, "unmatched")
            await db.commit()
            return {"success": True}

        # Don da huy: khong danh dau paid, can hoan tien thu cong
        if order.status == "cancelled":
            logger.warning(
                "SePay: don %s da huy nhung van nhan tien. Can xu ly hoan tien thu cong.",
                order_code,
            )
            _mark_webhook_status(log_row, "cancelled")
            await db.commit()
            return {"success": True}

        # Chinh sach amount mismatch: thieu tien -> KHONG danh paid
        if payload.amount_in < int(order.total):
            logger.warning(
                "SePay: don %s nhan thieu tien (nhan=%s, can=%s). Chua danh paid.",
                order_code,
                payload.amount_in,
                order.total,
            )
            _mark_webhook_status(log_row, "amount_mismatch")
            await db.commit()
            return {"success": True}

        if payload.amount_in > int(order.total):
            logger.info(
                "SePay: don %s nhan thua tien (nhan=%s, can=%s). Van danh paid.",
                order_code,
                payload.amount_in,
                order.total,
            )

        await order_service.update_payment_status(
            db,
            order_code=order_code,
            transaction_id=transaction_id,
        )
        _mark_webhook_status(log_row, "processed")
        await db.commit()
        logger.info("SePay: da danh paid don %s (tx=%s).", order_code, transaction_id)
    except order_service.DuplicateTransactionError as exc:
        # Giao dich da gan cho don khac (unique index DB chan - race condition).
        # Da idempotent o tang app nen tra 200 cho SePay khong retry vo ich.
        logger.warning("SePay: %s", exc)
        await db.rollback()
        return {"success": True}
    except Exception as exc:
        logger.exception("SePay webhook failed for order %s", order_code)
        await db.rollback()
        # Tra 500 de SePay retry thay vi mat giao dich
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Webhook processing failed", "code": "INTERNAL_ERROR"},
        ) from exc

    return {"success": True}


@router.get("/status/{order_id}", response_model=dict)
async def get_payment_status(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Lay trang thai thanh toan cua don hang.
    Chi chu don hoac admin moi xem duoc.
    """
    order = await order_service.get_order_by_id(db, order_id)

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Không tìm thấy đơn hàng", "code": "NOT_FOUND"},
        )

    if order.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Không có quyền xem đơn hàng này", "code": "FORBIDDEN"},
        )

    return {
        "data": {
            "order_code": order.order_code,
            "payment_status": order.payment_status,
            "paid_at": order.paid_at,
        },
        "message": "OK",
    }


@router.post("/reconcile", response_model=dict)
async def reconcile_payments(
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Chay doi soat thanh toan thu cong (admin): quet SePay API v2 va danh paid don con thieu.
    """
    stats = await payment_reconcile_service.reconcile_pending_orders(db)
    return {"data": stats, "message": "OK"}
