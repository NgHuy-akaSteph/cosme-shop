"""
Kiem tra cau hinh thanh toan luc khoi dong app (fail-fast).

Muc dich: bat loi cau hinh SePay SOM thay vi de no xay ra luc co giao dich
that -> tien vao tai khoan nhung don ket `unpaid` (mat tien im lang).

Cac loi duoc CHECK (raise ValueError -> app khong start):
- `SEPAY_PAYMENT_CODE_PREFIX` phai 2-5 ky tu (quy dinh SePay).
- `SEPAY_PAYMENT_CODE_SUFFIX_LENGTH` phai 1..30.
- Tong do dai ma <= 32 (gioi han cot `orders.order_code`).
- `SEPAY_QR_CONTENT_PREFIX` phai chua "SEVQR" khi ngan hang la VietinBank
  (VietinBank ca nhan/ho kinh doanh BAT BUOC "SEVQR" trong noi dung chuyen
  khoan; thieu chuoi nay SePay KHONG day giao dich ve webhook).

Cac loi duoc CANH BAO (log, app van start):
- Thieu `SEPAY_BANK_ACCOUNT` -> khong sinh duoc QR.
- Thieu `SEPAY_WEBHOOK_SECRET` -> webhook fallback sang API key (it an toan hon).
- Thieu `SEPAY_API_TOKEN` -> khong chay duoc doi soat giao dich.
"""

import logging

from app.core.config import settings
from app.payment.payment_code import (
    MAX_ORDER_CODE_LENGTH,
    MAX_PREFIX_LENGTH,
    MIN_PREFIX_LENGTH,
)

logger = logging.getLogger(__name__)

# VietinBank (ca nhan / ho kinh doanh) yeu cau chuoi nay trong noi dung CK.
VietinBank_REQUIRED_CONTENT_PREFIX = "SEVQR"
# Ma ngan hang trong `vietqr.app/banks.json` cua VietinBank.
VietinBank_SHORT_CODE = "ICB"


def check_payment_config() -> list[str]:
    """
    Kiem tra cau hinh thanh toan.

    Returns:
        Danh sach canh bao (khong chan app start).

    Raises:
        ValueError: khi cau hinh sai nghiem trong -> app nen khong start.
    """
    errors: list[str] = []
    warnings: list[str] = []

    prefix = settings.SEPAY_PAYMENT_CODE_PREFIX.strip().upper()
    suffix_len = int(settings.SEPAY_PAYMENT_CODE_SUFFIX_LENGTH)

    # 1. Tien to ma thanh toan
    if not (MIN_PREFIX_LENGTH <= len(prefix) <= MAX_PREFIX_LENGTH):
        errors.append(
            f"SEPAY_PAYMENT_CODE_PREFIX='{prefix}' phai tu {MIN_PREFIX_LENGTH} den "
            f"{MAX_PREFIX_LENGTH} ky tu (quy dinh SePay)."
        )

    # 2. Do dai hau to
    if not (1 <= suffix_len <= 30):
        errors.append(
            f"SEPAY_PAYMENT_CODE_SUFFIX_LENGTH={suffix_len} phai tu 1 den 30."
        )

    # 3. Tong do dai ma <= gioi han cot `orders.order_code`
    if len(prefix) + suffix_len > MAX_ORDER_CODE_LENGTH:
        errors.append(
            f"Tong do dai ma thanh toan ({len(prefix) + suffix_len}) vuot qua "
            f"{MAX_ORDER_CODE_LENGTH} (cot `orders.order_code`)."
        )

    # 4. VietinBank bat buoc "SEVQR" trong noi dung chuyen khoan
    content_prefix = settings.SEPAY_QR_CONTENT_PREFIX.strip()
    bank_name = settings.SEPAY_BANK_NAME.strip().upper()
    if bank_name == VietinBank_SHORT_CODE and VietinBank_REQUIRED_CONTENT_PREFIX not in content_prefix:
        errors.append(
            f"Ngan hang VietinBank (bank='{bank_name}') BAT BUOC chuoi "
            f"'{VietinBank_REQUIRED_CONTENT_PREFIX}' trong noi dung chuyen khoan "
            f"(SEPAY_QR_CONTENT_PREFIX). Hien tai='{content_prefix}'."
            " Thieu chuoi nay SePay KHONG day giao dich ve webhook => mat tien."
        )

    # 5. Canh bao (khong chan start)
    if not settings.SEPAY_BANK_ACCOUNT:
        warnings.append(
            "SEPAY_BANK_ACCOUNT rong -> khong sinh duoc QR VietQR cho don sepay."
        )
    if not settings.SEPAY_WEBHOOK_SECRET:
        warnings.append(
            "SEPAY_WEBHOOK_SECRET rong -> webhook xac thuc bang API key "
            "(it an toan HMAC-SHA256 + chong replay)."
        )
    if not settings.SEPAY_API_TOKEN:
        warnings.append(
            "SEPAY_API_TOKEN rong -> khong chay duoc doi soat giao dich (reconcile)."
        )

    for message in warnings:
        logger.warning("Cau hinh thanh toan: %s", message)

    if errors:
        raise ValueError(
            "Cau hinh thanh toan khong hop le:\n- " + "\n- ".join(errors)
        )

    return warnings
