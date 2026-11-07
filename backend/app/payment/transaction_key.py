"""Khoa chong trung giao dich, on dinh giua webhook va doi soat.

SePay cung cap 2 nguon ID cho CUNG 1 giao dich that:

| Nguon       | `id`                            | `referenceCode` / `reference_number` |
|-------------|--------------------------------|--------------------------------------|
| Webhook     | `44843` (int)                  | `SB2787C335AAF1`                     |
| API v2      | `37dcdb04-d85a-11f1-...` (UUID) | `SB2787C335AAF1`                   |

`reference_code` la ma tham chieu tu ngan hang => **on dinh giua 2 nguon**, nen
dung lam khoa chong trung. Neu dung `id`, 2 nguon se ghi 2 gia tri khac nhau
cho cung 1 giao dich => unique index `uq_orders_transaction_id` vo hieu =>
1 giao dich co the danh paid cho 2 don (mat tien).
"""

from typing import Any


def build_transaction_key(*, reference_code: str | None, transaction_id: Any) -> str:
    """
    Khoa chong trung cua 1 giao dich that.

    Uu tien `reference_code` (on dinh giua webhook va doi soat), fallback
    `transaction_id` (int hoac UUID) khi ngan hang khong gui ma tham chieu.
    """
    if reference_code and str(reference_code).strip():
        return str(reference_code).strip()
    return str(transaction_id)
