"""Trien khai cong thanh toan SePay"""

import json
import logging
import re
from typing import Any

from app.core.config import settings
from app.payment.base import PaymentLink
from app.schemas.payment import SePayWebhookPayload
from app.service.payment_security_service import (
    authenticate_webhook_request,
)

logger = logging.getLogger(__name__)

ORDER_CODE_PATTERN = re.compile(r"ORD\d+")


class SePayProvider:
    """Cong thanh toan SePay: QR VietQR + webhook HMAC/API key."""

    name = "sepay"

    def create_payment_link(self, order: Any) -> PaymentLink:
        """Dung QR URL VietQR cho don sepay chua thanh toan."""
        if not settings.SEPAY_BANK_ACCOUNT:
            return PaymentLink(provider=self.name)

        qr_url = (
            f"https://qr.sepay.vn/img?"
            f"acc={settings.SEPAY_BANK_ACCOUNT}"
            f"&bank={settings.SEPAY_BANK_NAME or ''}"
            f"&amount={order.total}"
            f"&des={order.order_code}"
        )
        return PaymentLink(
            provider=self.name,
            qr_url=qr_url,
            instruction=f"Chuyen khoan {order.total} VND noi dung {order.order_code}",
        )

    def verify_webhook(
        self, raw_body: bytes, headers: dict[str, str]
    ) -> tuple[bool, Any]:
        """
        Xac thuc HMAC-SHA256 (uu tien) hoac API key.

        Returns:
            (ok, SePayWebhookPayload | error_code)
        """
        ok, error = authenticate_webhook_request(
            raw_body,
            headers.get("authorization"),
            headers.get("x-sepay-signature"),
            headers.get("x-sepay-timestamp"),
        )
        if not ok:
            return False, error

        try:
            payload = SePayWebhookPayload.model_validate(json.loads(raw_body or b"{}"))
        except Exception as exc:
            logger.warning("SePay: payload khong khop schema: %s", exc)
            return False, "invalid_payload"

        return True, payload

    def extract_order_code(self, payload: Any) -> str | None:
        """Uu tien code > sub_account > content."""
        for candidate in (payload.code, payload.sub_account):
            if candidate:
                match = ORDER_CODE_PATTERN.search(candidate)
                if match:
                    return match.group(0)

        match = ORDER_CODE_PATTERN.search(payload.content or "")
        return match.group(0) if match else None
