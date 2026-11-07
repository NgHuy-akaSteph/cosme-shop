"""Sinh va kiem tra dinh dang "ma thanh toan" (order_code) theo mau SePay.

SePay boc tach `code` tu noi dung chuyen khoan theo *mau ma thanh toan* khai bao
trong dashboard (Cong ty -> Cau hinh chung -> Cau truc ma thanh toan). Mau phai
khop DUNG dinh dang ma shop sinh ra, neu khong SePay bo qua giao dich (tien vao
tai khoan nhung don ket `unpaid`).

Day la nguon su that duy nhat cho:
- tien to + do dai hau to cua ma thanh toan
- regex trich ma don tu payload webhook va noi dung giao dich
- validate fail-fast truoc khi sinh QR (QR sai = mat tien)
"""

import random
import re
from datetime import datetime, timezone

from app.core.config import settings

# `orders.order_code` la String(32) - ma thanh toan khong duoc vuot qua.
MAX_ORDER_CODE_LENGTH = 32
# SePay quy dinh tien to ma thanh toan 2-5 ky tu.
MIN_PREFIX_LENGTH = 2
MAX_PREFIX_LENGTH = 5


def payment_code_prefix() -> str:
    """Tien to ma thanh toan (VD: `ORD`) - luon normalize sang uppercase."""
    return settings.SEPAY_PAYMENT_CODE_PREFIX.strip().upper()


def payment_code_suffix_length() -> int:
    """Do dai hau to ma thanh toan (chu so) - VD: 12 cho `ORD` + YYYYMMDD + 4 so."""
    return int(settings.SEPAY_PAYMENT_CODE_SUFFIX_LENGTH)


def payment_code_pattern() -> re.Pattern[str]:
    r"""
    Regex trich ma don tu chuoi bat ky (payload `code`, `subAccount`, `content`).

    `<prefix>` + `<suffix_len>` chu so. KHONG them lookahead `(?!\d)` de khong
    bo qua ma khi noi dung chuyen khoan co them chu so phia sau (VD: ngan hang
    them du lieu) - SePay cung cat theo mau `ORD` + 12 so nen giu hành vi
    "cat nganh ma" cho khop.
    """
    prefix = re.escape(payment_code_prefix())
    return re.compile(rf"{prefix}\d{{{payment_code_suffix_length()}}}")


def is_valid_payment_code(code: str | None) -> bool:
    """Ma co khop dung mau ma SePay trich ra khong."""
    if not code:
        return False
    pattern = rf"{re.escape(payment_code_prefix())}\d{{{payment_code_suffix_length()}}}"
    return bool(re.fullmatch(pattern, code))


def validate_payment_code(code: str | None) -> str:
    """
    Fail-fast: nem loi neu ma khong khop mau ma SePay.

    Called truoc khi sinh QR - sinh QR sai dong nghia la mat tien that.
    """
    if not code:
        raise ValueError("Thieu ma thanh toan (order_code).")
    if not is_valid_payment_code(code):
        raise ValueError(
            "Ma thanh toan khong khop mau ma SePay: "
            f"'{code}' (mong doi {payment_code_prefix()}"
            f"+{payment_code_suffix_length()} chu so). "
            "Kiem tra lai cau hinh mau ma thanh toan tren dashboard SePay."
        )
    return code


def build_payment_code() -> str:
    """
    Sinh ma thanh toan: `<prefix>` + `YYYYMMDD` + phan random, het do dai hau to.

    Do dai hau to lay tu config nen doi `SEPAY_PAYMENT_CODE_SUFFIX_LENGTH` chi can
    sua 1 cho (va doi mau ma tren dashboard SePay cho khop).
    """
    prefix = payment_code_prefix()
    suffix_len = payment_code_suffix_length()

    if not (MIN_PREFIX_LENGTH <= len(prefix) <= MAX_PREFIX_LENGTH):
        raise ValueError(
            f"Tien to ma thanh toan '{prefix}' phai tu {MIN_PREFIX_LENGTH} den "
            f"{MAX_PREFIX_LENGTH} ky tu (quy dinh SePay)."
        )
    if suffix_len < 1:
        raise ValueError("Do dai hau to ma thanh toan phai >= 1.")
    if len(prefix) + suffix_len > MAX_ORDER_CODE_LENGTH:
        raise ValueError(
            f"Do dai ma thanh toan ({len(prefix) + suffix_len}) vuot qua gioi han "
            f"{MAX_ORDER_CODE_LENGTH} (cot `orders.order_code`)."
        )

    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")[:suffix_len]
    random_part = "".join(str(random.randint(0, 9)) for _ in range(suffix_len - len(date_part)))

    return f"{prefix}{date_part}{random_part}"
