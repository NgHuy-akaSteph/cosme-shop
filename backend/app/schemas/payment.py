"""Pydantic schemas cho payment (SePay)"""

from pydantic import BaseModel, ConfigDict, Field


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

    transaction_id: int = Field(..., alias="id")
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
