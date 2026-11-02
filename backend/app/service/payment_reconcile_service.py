"""Doi soat thanh toan: quet giao dich tu SePay API v2 de bu webhook bi lo"""

import logging
import re
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.model.order import Order
from app.service import order_service

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 15.0
ORDER_CODE_PATTERN = re.compile(r"ORD\d+")


async def fetch_recent_transactions(days: int = 3) -> list[dict]:
    """
    Lay danh sach giao dich tien vao gan day tu SePay API v2.
    Tra ve [] neu thieu config hoac API loi (doi soat la best-effort).
    """
    if not settings.SEPAY_API_TOKEN:
        logger.warning("SePay reconcile: thieu SEPAY_API_TOKEN, bo qua.")
        return []

    since = datetime.now(timezone.utc) - timedelta(days=days)
    params = {
        "transaction_date_from": since.strftime("%Y-%m-%d"),
        "transaction_date_to": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    url = f"{settings.SEPAY_API_BASE_URL.rstrip('/')}/transactions"

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {settings.SEPAY_API_TOKEN}"},
            )
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        logger.warning("SePay reconcile: goi API that bai: %s", exc)
        return []

    if body.get("status") != "success":
        logger.warning("SePay reconcile: API tra status=%s", body.get("status"))
        return []

    return [tx for tx in body.get("data", []) if tx.get("transfer_type") == "in"]


async def reconcile_pending_orders(db, days: int = 3) -> dict[str, int]:
    """
    Quet giao dich chua khop va danh paid cho don sepay con unpaid.

    Returns:
        Thong ke {scanned, matched, marked_paid, skipped}
    """
    transactions = await fetch_recent_transactions(days)
    stats = {"scanned": len(transactions), "matched": 0, "marked_paid": 0, "skipped": 0}

    pending_orders = await db.execute(
        select(Order).where(
            Order.payment_method == "sepay",
            Order.payment_status == "unpaid",
            Order.status != "cancelled",
        )
    )
    orders = {order.order_code: order for order in pending_orders.scalars().all()}

    for tx in transactions:
        content = tx.get("transaction_content") or ""
        code = tx.get("code") or ""
        match = ORDER_CODE_PATTERN.search(f"{code} {content}")
        if not match:
            continue

        order_code = match.group(0)
        order = orders.get(order_code)
        if order is None:
            continue

        stats["matched"] += 1
        amount_in = int(tx.get("amount_in") or 0)
        if amount_in < int(order.total):
            stats["skipped"] += 1
            logger.warning(
                "SePay reconcile: don %s thieu tien (nhan=%s, can=%s).",
                order_code,
                amount_in,
                order.total,
            )
            continue

        await order_service.update_payment_status(
            db,
            order_code=order_code,
            transaction_id=str(tx.get("id")),
        )
        stats["marked_paid"] += 1
        logger.info(
            "SePay reconcile: da danh paid don %s (tx=%s).", order_code, tx.get("id")
        )

    return stats
