"""Trien khai cong thanh toan SePay"""

import json
import logging
from decimal import Decimal
from typing import Any
from urllib.parse import quote

from app.core.config import settings
from app.payment.base import PaymentLink
from app.payment.payment_code import (
    payment_code_pattern,
    validate_payment_code,
)
from app.schemas.payment import SePayWebhookPayload
from app.service.payment_security_service import (
    authenticate_webhook_request,
)

logger = logging.getLogger(__name__)


def format_vnd_amount(total: Any) -> str:
    """
    Chuyen tong tien thanh chuoi so nguyen VND cho tham so `amount` cua VietQR.

    `order.total` la Decimal (Numeric(12,0)) nhung Python render co the ra
    "430000.0" hoac "1.00E+6" - VietQR chi nhan so nguyen nen phai
    ep ve int truoc. Khong ep thi QR sinh ra khong dung so tien.
    """
    if isinstance(total, Decimal):
        return str(int(total))
    return str(int(Decimal(str(total))))


class SePayProvider:
    """Cong thanh toan SePay: QR VietQR + webhook HMAC/API key."""

    name = "sepay"

    def _build_transfer_content(self, order_code: str) -> str:
        """
        Noi dung chuyen khoan cua QR.

        VietinBank (ca nhan / ho kinh doanh) yeu cau chuoi "SEVQR" trong noi
        dung - thieu chuoi nay giao dich khong duoc SePay day ve webhook.

        `SEVQR` (yeu cau ngan hang) va `ORD` (ma thanh toan SePay) la 2 thu
        khac nhau: chi `ORD...` moi duoc SePay boc tach thanh `code`.
        """
        bank_prefix = settings.SEPAY_QR_CONTENT_PREFIX.strip()
        if not bank_prefix:
            return order_code
        return f"{bank_prefix} {order_code}"

    def create_payment_link(self, order: Any) -> PaymentLink:
        """
        Dung QR URL VietQR cho don sepay chua thanh toan.

        Fail-fast neu `order_code` khong khop mau ma SePay: QR sai chung nghia
        la giao dich thu tien khong bao gio duoc SePay day ve webhook.
        """
        if not settings.SEPAY_BANK_ACCOUNT:
            return PaymentLink(provider=self.name)

        order_code = validate_payment_code(order.order_code)
        amount = format_vnd_amount(order.total)
        content = self._build_transfer_content(order_code)
        qr_url = (
            f"{settings.SEPAY_QR_BASE_URL}?"
            f"acc={quote(settings.SEPAY_BANK_ACCOUNT, safe='')}"
            f"&bank={quote(settings.SEPAY_BANK_NAME or '', safe='')}"
            f"&amount={amount}"
            f"&des={quote(content, safe='')}"
        )
        return PaymentLink(
            provider=self.name,
            qr_url=qr_url,
            instruction=f"Chuyen khoan {amount} VND noi dung {content}",
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
        pattern = payment_code_pattern()
        for candidate in (payload.code, payload.sub_account):
            if candidate:
                match = pattern.search(candidate)
                if match:
                    return match.group(0)

        match = pattern.search(payload.content or "")
        return match.group(0) if match else None
