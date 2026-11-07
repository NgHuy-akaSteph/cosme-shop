"""Pydantic schemas cho payment (SePay)"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _to_int(value: Any) -> int:
    """SePay co the gui so tien duoi dang chuoi -> ep ve int."""
    return int(float(value))


class SePayWebhookPayload(BaseModel):
    """
    Payload webhook SePay (camelCase theo tai lieu chinh thuc).

    Vi du:
        {
          "id": 92704,
          "gateway": "Vietcombank",
          "transactionDate": "2024-07-02 11:08:33",
          "accountNumber": "1017588888",
          "subAccount": "",
          "code": "SEVN63DC8E5C",
          "content": "SEVN63DC8E5C chuyen tien",
          "transferType": "in",
          "description": "NGUYEN VAN A chuyen tien",
          "transferAmount": 5000000,
          "accumulated": 105000000,
          "referenceCode": "FT24012345678"
        }
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    # `id` là khoá giao dịch. Tài liệu webhook ghi là integer, nhưng API v2
    # (`/v2/transactions`) trả `id` là UUID string → chấp nhận cả hai,
    # chuẩn hoá về str. Khoá chống trùng thực sự dùng `reference_code`
    # (xem `app.payment.transaction_key`).
    transaction_id: str = Field(..., alias="id")
    gateway: str | None = None
    transaction_time: str | None = Field(None, alias="transactionDate")
    account_number: str | None = Field(None, alias="accountNumber")
    sub_account: str | None = Field(None, alias="subAccount")
    code: str | None = None
    content: str = ""
    transfer_type: str = Field(..., alias="transferType")
    description: str | None = None
    amount_in: int = Field(..., alias="transferAmount")
    accumulated: int = Field(0, alias="accumulated")
    reference_code: str | None = Field(None, alias="referenceCode")

    @field_validator("transaction_id", mode="before")
    @classmethod
    def _coerce_transaction_id(cls, value: Any) -> str:
        """`id` có thể là int (webhook) hoặc UUID string (API v2) → str."""
        return str(value)

    @field_validator("amount_in", "accumulated", mode="before")
    @classmethod
    def _coerce_amount(cls, value: Any) -> int:
        """Số tiền có thể được gửi dưới dạng chuỗi → int."""
        if value is None or value == "":
            return 0
        return _to_int(value)
