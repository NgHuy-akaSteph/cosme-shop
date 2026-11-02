"""Interface chung cho cac cong thanh toan (SePay, payOS sau nay)"""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class PaymentLink:
    """Ket qua tao link/QR thanh toan cho 1 don."""

    provider: str
    redirect_url: str | None = None   # URL thanh toan (payOS checkoutUrl)
    qr_url: str | None = None         # QR image URL (SePay)
    instruction: str | None = None    # huong dan cho nguoi mua


class PaymentProvider(Protocol):
    """Contract moi cong thanh toan phai ho tro."""

    name: str

    def create_payment_link(self, order: Any) -> PaymentLink:
        """Tao link/QR thanh toan cho order (chua ghi DB)."""
        ...

    def verify_webhook(self, raw_body: bytes, headers: dict[str, str]) -> tuple[bool, Any]:
        """
        Xac thuc webhook.

        Args:
            raw_body: Raw body cua request (bat buoc dung raw de kiem tra HMAC).
            headers: Header cua request (lower-case key).

        Returns:
            (ok, payload hoac error_code)
        """
        ...

    def extract_order_code(self, payload: Any) -> str | None:
        """Trich ma don tu payload webhook da xac thuc."""
        ...
