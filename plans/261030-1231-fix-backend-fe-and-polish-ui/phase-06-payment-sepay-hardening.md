# Phase 06 — Payment SePay hardening (hướng A: giữ SePay, làm chắc + mở đường cho payOS)

Context links: `backend/app/api/payment.py`, `backend/app/service/order_service.py`,
`backend/app/model/order.py`, `backend/app/core/config.py`, `backend/app/schemas/order.py`,
`backend/alembic/versions/`, `backend/.env.example`,
`docs/01-system-design.md`, `docs/02-business-requirement.md`, `docs/03-tech-stack.md`, `docs/04-database.md`.

Priority: P0 (R1–R4 là lỗi mất tiền tiềm ẩn) / P1 (R5–R6) · Status: ✅ Hoàn thành (2026-10-31)

> **Quyết định chiến lược (đã chốt):** giữ SePay làm kênh thanh toán chính.
> payOS **không** triển khai ở phase này (không có sandbox, đổi cả luồng thanh toán,
> `orderCode` phải là integer, `description` giới hạn 9 ký tự → rủi ro cao hơn giá trị
> ở giai đoạn hiện tại). Phase này chỉ:
> 1. Vá 2 lỗi "chạy được nhưng không nhận tiền" đã phát hiện.
> 2. Siết bảo mật + idempotent + khả năng đối soát (reconcile).
> 3. Tách lớp provider để sau này cắm payOS mà không phải viết lại nghiệp vụ.
>
> Tài liệu tham chiếu:
> - Webhook payload + phản hồi hợp lệ + chống trùng: https://developer.sepay.vn/vi/sepay-webhooks/tich-hop-webhook
> - Xác thực HMAC-SHA256: https://developer.sepay.vn/vi/sepay-webhooks/xac-thuc
> - API v2 tra cứu giao dịch: https://developer.sepay.vn/vi/sepay-api/v2/bat-dau-nhanh

## Yêu cầu

R1. **Sửa lỗi tên field của webhook SePay** (camelCase, không phải snake_case) — đây là lỗi khiến đơn không bao giờ chuyển `paid` mà không báo lỗi.
R2. **Idempotent ở mức DB** bằng `transaction_id` unique + bảng log webhook, chống cộng tiền/đánh dấu paid trùng khi SePay retry hoặc admin replay.
R3. **Xác thực HMAC-SHA256** (`X-SePay-Signature` + `X-SePay-Timestamp`) trên raw body, chống replay (timestamp lệch > 300s).
R4. **Chốt chính sách amount mismatch** và thống nhất với tài liệu dự án.
R5. **Fallback đối soát (reconcile)** qua SePay API v2 khi webhook không tới (mất mạng, tunnel chết).
R6. **Tách lớp provider** (`app/payment/`) để sẵn sàng cắm payOS sau, không phải viết lại nghiệp vụ.
R7. **Logging/observability** để phát hiện sớm webhook hỏng.
R8. **Cập nhật docs** cho khớp code mới.

## R1 — Sửa lỗi tên field webhook (P0, lỗi mất tiền)

**Hiện trạng (sai):** `backend/app/api/payment.py` khai báo model:

```python
class SePayWebhookPayload(BaseModel):
    content: str
    amount_in: float | None = None
    transfer_type: str | None = None
    transaction_id: str | None = None
    transaction_time: str | None = None
```

Nhưng payload thật của SePay là **camelCase**:

```json
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
```

→ `transfer_type` luôn là `None` → dòng `if payload.transfer_type != "in": return {"success": True}` **trả về im lặng**, đơn không bao giờ `paid`, không lỗi, không cảnh báo.
→ `amount_in` luôn `None` → nhánh "amount không đủ" cũng luôn chạy.

**Cách sửa:** dùng `alias` trong Pydantic để nhận đúng tên field thật.

```python
class SePayWebhookPayload(BaseModel):
    """Payload webhook SePay (camelCase theo tai lieu chinh thuc)."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    transaction_id: int = Field(..., alias="id")
    gateway: str | None = None
    transaction_time: str | None = Field(None, alias="transactionDate")
    account_number: str | None = Field(None, alias="accountNumber")
    sub_account: str | None = Field(None, alias="subAccount")
    code: str | None = None
    content: str
    transfer_type: str = Field(..., alias="transferType")
    description: str | None = None
    amount_in: int = Field(..., alias="transferAmount")
    accumulated: int = Field(0, alias="accumulated")
    reference_code: str | None = Field(None, alias="referenceCode")
```

Cần thêm import: `from pydantic import BaseModel, ConfigDict, Field`.

Lưu ý:
- `transferAmount` là **integer VND**, không phải float → dùng `int`. `Decimal(str(...))` vẫn OK nhưng `int` đơn giản hơn.
- `extra="ignore"` để payload có thêm field mới không làm 422 (SePay có thể bổ sung field).
- `sub_account` chính là **VA** khớp giao dịch — nếu sau này dùng VA theo đơn thì ưu tiên `sub_account`/`code` trước `content`.
- `id` của SePay **không đổi qua mọi lần retry/replay** → dùng làm khóa chống trùng (R2).

**Thứ tự ưu tiên trích mã đơn** (thay vì chỉ regex `ORD\d+` trong `content`):

1. `code` — mã thanh toán SePay trích theo cấu trúc mà ta cấu hình ở dashboard (khuyến nghị cấu hình prefix `ORD` ở SePay để `code` = mã đơn).
2. `sub_account` — VA nội dung, nếu dùng VA theo đơn.
3. `content` — fallback regex `ORD\d+`.

```python
ORDER_CODE_PATTERN = re.compile(r"ORD\d+")

def extract_order_code(payload: SePayWebhookPayload) -> str | None:
    """Lay ma don tu payload webhook (uu tien code > sub_account > content)."""
    for candidate in (payload.code, payload.sub_account):
        if candidate:
            match = ORDER_CODE_PATTERN.search(candidate)
            if match:
                return match.group(0)
    match = ORDER_CODE_PATTERN.search(payload.content or "")
    return match.group(0) if match else None
```

## R2 — Idempotent ở mức DB (P0)

**Hiện trạng:** `update_payment_status` chỉ check `order.payment_status == "paid"` → idempotent ở mức ứng dụng. Nhưng:
- `transaction_id` chưa có unique constraint → không chặn được 2 giao dịch khác nhau cùng đánh dấu 1 đơn.
- Không có bảng log webhook → không đối soát được, không audit được, không replay an toàn.
- SePay tài liệu ghi rõ: cùng một giao dịch có thể tới nhiều lần do retry **và** do admin bấm "gửi lại" (replay cả log đã thành công).

**Cách sửa:** thêm bảng `payment_webhook_logs`.

Migration mới `backend/alembic/versions/20261031_0900_c1d2e3f4a5b6_add_payment_webhook_logs.py`:

```python
"""add payment webhook logs

Revision ID: c1d2e3f4a5b6
Revises: b9c4d5e6f7a8
Create Date: 2026-10-31 09:00:00.000000

- Bang payment_webhook_logs luu lai webhook SePay da nhan (chong trung o muc DB)
- Unique constraint tren (provider, transaction_id) de chan giao dich trung
- Unique index tren orders.transaction_id de 1 giao dich chi danh 1 don
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "b9c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_webhook_logs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("provider", sa.String(length=20), nullable=False, server_default="sepay"),
        sa.Column("transaction_id", sa.String(length=64), nullable=False),
        sa.Column("order_code", sa.String(length=32), nullable=True),
        sa.Column("amount", sa.BigInteger(), nullable=True),
        sa.Column("payload", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(length(20), nullable=False, server_default="received"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("provider", "transaction_id", name="uq_payment_webhook_provider_txid"),
    )
    op.create_index(
        "ix_payment_webhook_logs_order_code",
        "payment_webhook_logs",
        ["order_code"],
    )
    op.create_index(
        "ix_payment_webhook_logs_status",
        "payment_webhook_logs",
        ["status"],
    )
    # 1 giao dich chi duoc gan cho 1 don -> chan cong tien / danh paid trung
    op.create_index(
        "uq_orders_transaction_id",
        "orders",
        ["transaction_id"],
        unique=True,
        postgresql_where=sa.text("transaction_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_orders_transaction_id", table_name="orders")
    op.drop_index("ix_payment_webhook_logs_status", table_name="payment_webhook_logs")
    op.drop_index("ix_payment_webhook_logs_order_code", table_name="payment_webhook_logs")
    op.drop_table("payment_webhook_logs")
```

Lưu ý:
- `postgresql_where` → partial unique index, cho phép nhiều đơn có `transaction_id = NULL`.
- `sa.dialects.postgresql.JSONB` cần import `import sqlalchemy.dialects.postgresql` hoặc dùng `from sqlalchemy.dialects import postgresql` và `postgresql.JSONB()`. Bổ sung import rõ ràng.
- `down_revision` = `b9c4d5e6f7a8` (head hiện tại: `0acfe5aae4ff` → `a8b3c4d5e6f7` → `b9c4d5e6f7a8`).

Model mới `backend/app/model/payment_webhook_log.py`:

```python
"""Model log webhook thanh toan (chong trung, audit, doi soat)"""

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, IdMixin, TimestampMixin


class PaymentWebhookLog(Base, IdMixin, TimestampMixin):
    """Log 1 webhook thanh toan da nhan tu gateway."""

    __tablename__ = "payment_webhook_logs"

    provider: Mapped[str] = mapped_column(String(20), default="sepay", nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(64), nullable=False)
    order_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    amount: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="received", nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
```

Cập nhật `backend/app/db/session.py` — thêm import model để mapper được register:

```python
from app.model.payment_webhook_log import PaymentWebhookLog  # noqa: F401, E402
```

**Luồng xử lý webhook mới** (trong `backend/app/api/payment.py`):

```python
async def _record_webhook(
    db: AsyncSession,
    provider: str,
    transaction_id: str,
    order_code: str | None,
    amount: int | None,
    payload: dict,
    status: str,
    error: str | None = None,
) -> bool:
    """
    Ghi log webhook. Tra ve False neu da xu ly giao dich nay roi (trung).
    """
    existing = await db.execute(
        select(PaymentWebhookLog).where(
            PaymentWebhookLog.provider == provider,
            PaymentWebhookLog.transaction_id == transaction_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return False

    db.add(
        PaymentWebhookLog(
            provider=provider,
            transaction_id=transaction_id,
            order_code=order_code,
            amount=amount,
            payload=payload,
            status=status,
            error=error,
        )
    )
    return True
```

Trong webhook handler, sau khi verify + parse:

```python
is_new = await _record_webhook(
    db, "sepay", str(payload.transaction_id), order_code, payload.amount_in, raw_payload, "received"
)
if not is_new:
    logger.info("SePay: giao dich %s da duoc xu ly truoc, bo qua (idempotent).", payload.transaction_id)
    await db.commit()
    return {"success": True}
```

Sau khi xử lý thành công → cập nhật `status="processed"`, và khi lỗi → `status="failed"` + `error`.

**Sửa `update_payment_status`** trong `backend/app/service/order_service.py` để chống trùng ở mức đơn:

```python
async def update_payment_status(
    db: AsyncSession,
    order_code: str,
    transaction_id: str | None = None,
) -> Order | None:
    """
    Cap nhat trang thai thanh toan (webhook gateway).
    Idempotent: chi update neu chua paid; tu cho moi 1 transaction_id -> 1 don.
    """
    order = await get_order_by_code(db, order_code)
    if order is None:
        return None

    if order.payment_status == "paid":
        return order

    # 1 giao dich khong duoc gan cho 2 don khac nhau
    if transaction_id:
        dup = await db.execute(
            select(Order).where(
                Order.transaction_id == transaction_id,
                Order.id != order.id,
            )
        )
        if dup.scalar_one_or_none() is not None:
            logger.warning(
                "Transaction %s da duoc gan cho don khac, bo qua don %s",
                transaction_id, order_code,
            )
            return order

    order.payment_status = "paid"
    order.paid_at = datetime.now(timezone.utc).isoformat()
    if transaction_id:
        order.transaction_id = transaction_id

    await db.commit()
    return await get_order_by_id(db, order.id)
```

Cần thêm `from app.core.config import settings`? Không. Cần `logger` trong `order_service.py`:

```python
import logging

logger = logging.getLogger(__name__)
```

## R3 — Xác thực HMAC-SHA256 (P0)

SePay ký: `sha256={hex}` trên chuỗi `{timestamp}.{raw_body}`, header `X-SePay-Signature` và `X-SePay-Timestamp`.

**Điểm mấu chốt:** phải dùng **raw body**, không parse rồi serialize lại (sẽ lệch do escape Unicode/thứ tự key/whitespace).

Trong FastAPI, lấy raw body bằng `await request.body()` rồi tự parse JSON (không dùng Pydantic body param để tránh double-parse).

Tạo `backend/app/service/payment_security_service.py`:

```python
"""Xac thuc chu ky webhook (HMAC-SHA256) - chong gia mao + chong replay"""

import hashlib
import hmac
import logging
import time

from app.core.config import settings

logger = logging.getLogger(__name__)

# SePay chap nhan request trong toi da 300 giay
MAX_TIMESTAMP_SKEW_SECONDS = 300


def verify_webhook_signature(
    raw_body: bytes,
    signature: str | None,
    timestamp: str | None,
    secret: str | None,
) -> tuple[bool, str]:
    """
    Kiem tra chu ky HMAC-SHA256 cua SePay.

    Returns:
        (ok, error_code) - error_code: "missing_secret" | "missing_headers"
                           | "expired" | "invalid_signature" | ""
    """
    if not secret:
        return False, "missing_secret"

    if not signature or not timestamp:
        return False, "missing_headers"

    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False, "missing_headers"

    # Chong replay: request cu hon 5 phut -> reject
    if abs(time.time() - ts) > MAX_TIMESTAMP_SKEW_SECONDS:
        logger.warning("Webhook: timestamp %s lech qua %ss", ts, MAX_TIMESTAMP_SKEW_SECONDS)
        return False, "expired"

    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        f"{ts}.".encode("utf-8") + raw_body,
        hashlib.sha256,
    ).hexdigest()

    # constant-time compare
    if not hmac.compare_digest(expected.encode("utf-8"), signature.encode("utf-8")):
        logger.warning("Webhook: chu ky khong khop")
        return False, "invalid_signature"

    return True, ""
```

**Cấu hình mới** trong `backend/app/core/config.py`:

```python
    # SePay
    SEPAY_API_KEY: str = ""          # API Key xac thuc webhook (cach 1)
    SEPAY_WEBHOOK_SECRET: str = ""   # Secret Key HMAC-SHA256 (cach 2, khuyen nghi)
    SEPAY_BANK_ACCOUNT: str = ""
    SEPAY_BANK_NAME: str = ""
    SEPAY_API_TOKEN: str = ""        # Bearer token cho SePay API v2 (doi soat)
    SEPAY_API_BASE_URL: str = "https://userapi.sepay.vn/v2"
    # Sandbox: https://userapi-sandbox.sepay.vn/v2
```

**Quy tắc chọn cơ chế xác thực** (theo thứ tự ưu tiên, hỗ trợ cả hai để không phá endpoint cũ):

```python
def _authenticate_request(
    raw_body: bytes,
    authorization: str | None,
    signature: str | None,
    timestamp: str | None,
) -> tuple[bool, str]:
    """
    1. Neu co SEPAY_WEBHOOK_SECRET -> bat buoc HMAC-SHA256 (khuyen nghi).
    2. Neu khong co secret -> fallback API Key (de tam thu muc do).
    """
    if settings.SEPAY_WEBHOOK_SECRET:
        return verify_webhook_signature(raw_body, signature, timestamp, settings.SEPAY_WEBHOOK_SECRET)

    expected_key = settings.SEPAY_API_KEY
    prefix = "Apikey "
    provided = authorization[len(prefix):] if authorization and authorization.startswith(prefix) else ""
    if not expected_key or not hmac.compare_digest(provided.encode(), expected_key.encode()):
        return False, "invalid_api_key"
    return True, ""
```

Ghi chú an toàn: nếu cấu hình **cả hai** cùng rỗng → reject 401 (không để chuỗi rỗng khớp chuỗi rỗng). Logic trên đã đảm bảo điều này.

**Handler webhook viết lại** trong `backend/app/api/payment.py` (nhận `Request` thay vì Pydantic body):

```python
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

    ok, error = _authenticate_request(
        raw_body,
        request.headers.get("authorization"),
        request.headers.get("x-sepay-signature"),
        request.headers.get("x-sepay-timestamp"),
    )
    if not ok:
        logger.warning("SePay webhook: xac thuc that bai (%s)", error)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Unauthorized", "code": "UNAUTHORIZED"},
        )

    try:
        raw_payload = json.loads(raw_body or b"{}")
    except json.JSONDecodeError:
        logger.warning("SePay webhook: body khong phai JSON hop le")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Invalid payload", "code": "INVALID_PAYLOAD"},
        )

    try:
        payload = SePayWebhookPayload.model_validate(raw_payload)
    except ValidationError as exc:
        logger.warning("SePay webhook: payload khong khop schema: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Invalid payload", "code": "INVALID_PAYLOAD"},
        )

    # Chi xu ly tien vao
    if payload.transfer_type != "in":
        await _record_webhook(db, "sepay", str(payload.transaction_id), None, payload.amount_in, raw_payload, "ignored")
        await db.commit()
        return {"success": True}

    order_code = extract_order_code(payload)
    if not order_code:
        # Giao dich khong phai cua shop -> ghi log, tra success de SePay khong retry
        await _record_webhook(db, "sepay", str(payload.transaction_id), None, payload.amount_in, raw_payload, "unmatched")
        await db.commit()
        return {"success": True}

    try:
        is_new = await _record_webhook(
            db, "sepay", str(payload.transaction_id), order_code, payload.amount_in, raw_payload, "received"
        )
        if not is_new:
            logger.info("SePay: giao dich %s da xu ly truoc, bo qua.", payload.transaction_id)
            await db.commit()
            return {"success": True}

        order = await order_service.get_order_by_code(db, order_code)
        if order is None:
            await db.commit()
            return {"success": True}

        if order.status == "cancelled":
            logger.warning("SePay: don %s da huy nhung van nhan tien. Can xu ly hoan tien thu cong.", order_code)
            await _mark_webhook_status(db, payload.transaction_id, "cancelled")
            await db.commit()
            return {"success": True}

        await order_service.update_payment_status(
            db,
            order_code=order_code,
            transaction_id=str(payload.transaction_id),
        )
        await _mark_webhook_status(db, payload.transaction_id, "processed")
        await db.commit()
    except Exception as exc:
        logger.exception("SePay webhook failed for order %s", order_code)
        await db.rollback()
        # Tra 500 de SePay retry thay vi mat giao dich
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Webhook processing failed", "code": "INTERNAL_ERROR"},
        )

    return {"success": True}
```

**Phải trả đúng `{"success": true}` + HTTP 200/201 trong 30 giây** — tài liệu SePay coi là thất bại nếu sai body hoặc status khác 200/201, và sẽ retry tối đa 7 lần theo lịch Fibonacci (tối đa 5 giờ). Code hiện tại đã trả `{"success": True}` → FastAPI serialize thành `{"success":true}` → đúng format.

Lưu ý `raise HTTPException(500)` khi lỗi xử lý → handler trong `main.py` trả `content=detail` (dict) → status 500 → SePay retry. Đúng chủ ý.

## R4 — Chốt chính sách amount mismatch (P1)

**Bất đồng hiện tại:**
- Code: `if payload.amount_in is None or Decimal(str(payload.amount_in)) < order.total: log + return success` (thiếu tiền → **không** đánh paid).
- `docs/02-business-requirement.md` §SePay: "Amount không khớp → log warning, **vẫn update**".

**Quyết định (an toàn tài chính, chọn phương án 2):**

1. **Thiếu tiền** (`amount_in < total`) → **KHÔNG** đánh `paid`. Giữ `unpaid`, ghi log `payment_webhook_logs.status = "amount_mismatch"`, log warning kèm số tiền thực/nhận. Đơn vẫn hiển thị QR để khách chuyển bù.
   - Lý do: đánh paid khi thiếu tiền = lỗ tài chính trực tiếp. Số tiền thiếu có thể xử lý thủ công bởi admin.
2. **Thừa tiền** (`amount_in > total`) → đánh `paid` bình thường, log info ghi nhận chênh lệch. Thừa chuyển khoản là lỗi phía khách, không phải lỗi hệ thống.
3. **Đơn chưa tồn tại** → trả `{"success": true}` (đã có) + ghi log `unmatched`.

Cập nhật `docs/02-business-requirement.md` để khớp code (đổi "vẫn update" → "không cập nhật, ghi log, admin xử lý").

Sửa trong handler (thay block check amount hiện tại):

```python
        if payload.amount_in < int(order.total):
            logger.warning(
                "SePay: don %s nhan thieu tien (nhan=%s, can=%s). Chua danh paid.",
                order_code, payload.amount_in, order.total,
            )
            await _mark_webhook_status(db, payload.transaction_id, "amount_mismatch")
            await db.commit()
            return {"success": True}

        if payload.amount_in > int(order.total):
            logger.info(
                "SePay: don %s nhan thua tien (nhan=%s, can=%s). Van danh paid.",
                order_code, payload.amount_in, order.total,
            )
```

## R5 — Fallback đối soát qua SePay API v2 (P1)

**Bối cảnh:** nếu server/tunnel chết đúng lúc có giao dịch, webhook không tới → đơn kẹt `unpaid` dù đã thu tiền. Cần cơ chế chủ động quét lại.

SePay API v2 (Bearer token):

```
GET {BASE_URL}/transactions?transaction_date_from=2026-10-31&transaction_date_to=2026-10-31
Authorization: Bearer <SEPAY_API_TOKEN>
```

Response: `{"status": "success", "data": [...], "meta": {"pagination": {...}}}` với field: `id`, `transaction_date`, `account_number`, `va`, `transfer_type`, `amount_in`, `amount_out`, `accumulated`, `transaction_content`, `reference_number`, `code`, `bank_brand_name`.

Tạo `backend/app/service/payment_reconcile_service.py`:

```python
"""Doi soat thanh toan: quet giao dich tu SePay API v2 de bu webhook bi lo"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.model.order import Order
from app.service import order_service

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 15.0


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
    Tra ve thong ke {scanned, matched, marked_paid, skipped}.
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
        match = re.search(r"ORD\d+", f"{code} {content}")
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
            logger.warning("SePay reconcile: don %s thieu tien (nhan=%s, can=%s).", order_code, amount_in, order.total)
            continue

        await order_service.update_payment_status(
            db,
            order_code=order_code,
            transaction_id=str(tx.get("id")),
        )
        stats["marked_paid"] += 1
        logger.info("SePay reconcile: da danh paid don %s (tx=%s).", order_code, tx.get("id"))

    return stats
```

Cần `import re` ở đầu file.

**Kích hoạt:** thêm endpoint admin thủ công + (tuỳ chọn) cron.

Endpoint `backend/app/api/payment.py`:

```python
@router.post("/reconcile")
async def reconcile_payments(
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Chay doi soat thanh toan thu cong (admin): quet SePay API v2 va danh paid don con thieu."""
    stats = await payment_reconcile_service.reconcile_pending_orders(db)
    return {"data": stats, "message": "OK"}
```

Cần import `from app.api.deps import get_current_user, get_current_admin` và `from app.model.user import User`.

Ghi chú: **không** thêm cron/background task trong phase này (YAGNI). Endpoint thủ công đủ dùng cho demo và vận hành nhỏ. Nếu cần tự động hoá thì thêm APScheduler ở phase sau.

## R6 — Tách lớp provider (P1, chuẩn bị payOS)

Mục tiêu: business logic (tạo đơn, trạng thái, idempotent) không còn gắn cứng với SePay. Khi cắm payOS chỉ thêm provider mới + đổi registry.

Cấu trúc mới:

```
backend/app/payment/
├── __init__.py            # export registry
├── base.py                # PaymentProvider protocol + PaymentLink dataclass
├── sepay_provider.py      # trien khai SePay
└── registry.py            # get_provider()
```

`backend/app/payment/base.py`:

```python
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

    def verify_webhook(self, request: Any) -> tuple[bool, Any]:
        """Xac thuc webhook. Tra (ok, payload hoac error_code)."""
        ...

    def extract_order_code(self, payload: Any) -> str | None:
        """Trich ma don tu payload webhook da xac thuc."""
        ...
```

`backend/app/payment/sepay_provider.py`:

```python
"""Trien khai cong thanh toan SePay"""

import json
import logging
import re
from typing import Any

from app.core.config import settings
from app.payment.base import PaymentLink
from app.schemas.payment import SePayWebhookPayload

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

    def verify_webhook(self, request: Any) -> tuple[bool, Any]:
        """Xac thuc HMAC-SHA256 (uu tien) hoac API key. Tra (ok, payload|error_code)."""
        from app.service.payment_security_service import verify_webhook_signature

        raw_body = request.body()

        if settings.SEPAY_WEBHOOK_SECRET:
            ok, error = verify_webhook_signature(
                raw_body,
                request.headers.get("x-sepay-signature"),
                request.headers.get("x-sepay-timestamp"),
                settings.SEPAY_WEBHOOK_SECRET,
            )
            if not ok:
                return False, error
        else:
            ok, error = _verify_api_key(request.headers.get("authorization"))
            if not ok:
                return False, error

        try:
            payload = SePayWebhookPayload.model_validate(json.loads(raw_body or b"{}"))
        except Exception:
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
```

`backend/app/payment/registry.py`:

```python
"""Registry cac cong thanh toan"""

from app.core.config import settings
from app.payment.base import PaymentProvider
from app.payment.sepay_provider import SePayProvider

_PROVIDERS: dict[str, PaymentProvider] = {
    "sepay": SePayProvider(),
}


def get_provider(name: str | None = None) -> PaymentProvider:
    """
    Tra ve provider theo ten (mac dinh theo payment_method cua don).
    Sau nay them payOS: chi can dang ky vao _PROVIDERS.
    """
    key = name or "sepay"
    provider = _PROVIDERS.get(key)
    if provider is None:
        raise KeyError(f"Payment provider chua duoc ho tro: {key}")
    return provider
```

`backend/app/payment/__init__.py`:

```python
""" Lop thanh toan: interface chung + registry cac provider """

from app.payment.base import PaymentLink, PaymentProvider
from app.payment.registry import get_provider

__all__ = ["PaymentLink", "PaymentProvider", "get_provider"]
```

**Schema tách riêng:** chuyển `SePayWebhookPayload` từ `backend/app/api/payment.py` sang `backend/app/schemas/payment.py` (file mới, ~30 dòng) để provider có thể import mà không tạo phụ thuộc vòng với `app.api`.

**Refactor `backend/app/service/order_service.py`:**

Thay đoạn hardcode QR bằng:

```python
    # Generate QR URL cho SePay
    qr_url = None
    if payment_method == "sepay":
        from app.payment import get_provider

        provider = get_provider(payment_method)
        link = provider.create_payment_link(order)
        qr_url = link.qr_url
```

**Refactor `backend/app/api/payment.py`:** dùng `get_provider("sepay")` cho `verify_webhook` + `extract_order_code`, giữ phần HTTP/logic nghiệp vụ trong file.

Lưu ý: `order_service.py` import `app.payment` bên trong hàm (lazy import) để tránh circular import, tương tự pattern đang dùng cho `from app.core.config import settings`.

**Khi nào cắm payOS:** xem `docs/03-tech-stack.md` §"Hướng mở rộng" — chỉ cần:
1. `pip install payos` (không xung đột dependency: httpx 0.28.1 ✓, pydantic 2.13.5 ✓, typing-extensions 4.16 ✓).
2. Tạo `backend/app/payment/payos_provider.py` implement `PaymentProvider`.
3. Đăng ký vào `_PROVIDERS["payos"]`.
4. Thêm `payos_order_code` (integer) vào bảng `orders` + migration.
5. Thêm `payment_method='payos'` vào CHECK constraint `payment_method`.

## R7 — Logging/observability (P1)

Bổ sung vào `backend/app/api/payment.py` (hoặc `backend/app/core/logging.py` nếu có — hiện **chưa có** file này):

- `logging.basicConfig(level=logging.INFO)` chỉ khi khởi tạo app trong `main.py` (hiện `main.py` chưa cấu hình logging → log `logger.warning` có thể không hiện).
- Log mỗi webhook nhận: `transaction_id`, `order_code`, `amount_in`, `gateway`, kết quả xử lý.
- Log cảnh báo khi payload không khớp schema (R1) — đây là chỉ báo sớm cho lỗi cấu hình.
- Log mỗi lần đánh `paid`: order_code, transaction_id, paid_at.

Trong `main.py`:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
```

## R8 — Cập nhật docs (bắt buộc)

- `docs/03-tech-stack.md`:
  - Bảng env: thêm `SEPAY_WEBHOOK_SECRET`, `SEPAY_API_TOKEN`, `SEPAY_API_BASE_URL`.
  - Section API: thêm `POST /api/payment/reconcile` (admin).
  - Section "Hướng mở rộng": ghi rõ cách cắm payOS qua `app/payment/registry.py`.
- `docs/02-business-requirement.md`:
  - Sửa mô tả SePay webhook: payload camelCase, xác thực HMAC-SHA256, chính sách amount mismatch (R4), cơ chế idempotent DB.
- `docs/04-database.md`:
  - Thêm bảng `payment_webhook_logs` và unique index `uq_orders.transaction_id`.
- `docs/01-system-design.md`:
  - Cập nhật sequence diagram SePay: thêm bước verify HMAC + ghi log webhook + fallback reconcile.
- `backend/.env.example`: thêm 3 biến mới (giá trị rỗng, có comment giải thích).
- `docs/rules.md`: cập nhật cây thư mục `app/payment/` và `app/schemas/payment.py`.

## Files cần sửa

Backend — sửa:
- `backend/app/api/payment.py` (viết lại webhook handler, thêm endpoint reconcile)
- `backend/app/service/order_service.py` (dùng provider, chống trùng transaction_id)
- `backend/app/service/payment_security_service.py` (TẠO MỚI — verify HMAC/API key)
- `backend/app/service/payment_reconcile_service.py` (TẠO MỚI — đối soát API v2)
- `backend/app/model/payment_webhook_log.py` (TẠO MỚI)
- `backend/app/db/session.py` (register model mới)
- `backend/app/core/config.py` (3 biến env mới)
- `backend/app/main.py` (cấu hình logging)
- `backend/app/payment/__init__.py` (TẠO MỚI)
- `backend/app/payment/base.py` (TẠO MỚI)
- `backend/app/payment/sepay_provider.py` (TẠO MỚI)
- `backend/app/payment/registry.py` (TẠO MỚI)
- `backend/app/schemas/payment.py` (TẠO MỚI — `SePayWebhookPayload`)
- `backend/alembic/versions/20261031_0900_c1d2e3f4a5b6_add_payment_webhook_logs.py` (TẠO MỚI)
- `backend/.env.example`

Docs:
- `docs/01-system-design.md`, `docs/02-business-requirement.md`, `docs/03-tech-stack.md`, `docs/04-database.md`, `docs/rules.md`

Frontend: **không sửa** (polling + QR modal đã nằm ở phase-03 R5/R6).

## Todo

- [x] R1 đổi schema webhook sang camelCase + `extract_order_code` ưu tiên `code`
- [x] R2 migration `payment_webhook_logs` + unique `orders.transaction_id` + model + `update_payment_status` chống trùng
- [x] R3 `payment_security_service.py` + handler đọc raw body + HMAC + chống replay
- [x] R4 chốt chính sách amount mismatch + cập nhật docs
- [x] R5 `payment_reconcile_service.py` + endpoint `/api/payment/reconcile`
- [x] R6 tách `app/payment/` (base + sepay_provider + registry) + `app/schemas/payment.py` + refactor order_service/payment.py
- [x] R7 `logging.basicConfig` trong `main.py` + log chi tiết webhook
- [x] R8 cập nhật 5 file docs + `.env.example`
- [x] `cd backend && .venv/bin/python -c "import app.main"` (compile check)
- [x] `cd backend && .venv/bin/alembic upgrade head` (chạy migration)
- [x] Test webhook bằng payload mẫu (curl kèm HMAC tính sẵn) → đơn chuyển `paid`
- [x] Test lặp lại cùng payload → log `payment_webhook_logs` chỉ có 1 dòng, đơn không đổi
- [x] Test payload sai chữ ký → 401
- [x] Test amount thiếu → đơn vẫn `unpaid`, log `amount_mismatch`

## Success criteria

- Webhook payload **camelCase** thật (`transferType`, `transferAmount`, `id`) → đơn chuyển `paid` trong < 5s.
- Gửi lại cùng 1 payload 3 lần → `payment_webhook_logs` chỉ có 1 dòng `processed`; `orders.transaction_id` chỉ gán 1 lần; đơn không đổi trạng thái lần 2.
- Webhook thiếu/sai `X-SePay-Signature` (khi đã bật `SEPAY_WEBHOOK_SECRET`) → 401, đơn **không** chuyển paid.
- Webhook với timestamp lệch > 300s → 401.
- Webhook `transferAmount` < `order.total` → đơn giữ `unpaid`, log `payment_webhook_logs.status = "amount_mismatch"`.
- Webhook cho đơn `cancelled` → đơn không đổi, log có cảnh báo "cần hoàn tiền thủ công".
- `POST /api/payment/reconcile` với token admin → trả `{scanned, matched, marked_paid, skipped}`; chạy lại lần 2 → `marked_paid = 0` (idempotent).
- `POST /api/payment/reconcile` không token admin → 401/403.
- `app/payment/registry.py` có `get_provider("sepay")` trả về provider dùng được `create_payment_link()`.
- `alembic upgrade head` chạy sạch trên DB dev; `downgrade` không lỗi.

## Risk

- **Bật HMAC-SHA256 mà webhook cũ đang chạy với API Key** → SePay gọi webhook lên 401 liên tục. → Phải đổi cấu hình trên SePay **trước**, rồi deploy code, rồi set `SEPAY_WEBHOOK_SECRET`. Đề xuất: giữ fallback API Key trong code, chỉ bật HMAC khi env có secret.
- **Sai tên field** là lỗi đã xảy ra → sau khi sửa, các webhook cũ đang "thất bại im lặng" sẽ bắt đầu hoạt động → có thể có nhiều đơn chuyển paid đột ngột. Kiểm tra `payment_webhook_logs` sau khi deploy.
- **Partial unique index `orders.transaction_id`** → nếu DB hiện có 2 đơn cùng `transaction_id` (khó xảy ra vì đơn chưa từng được paid trùng) thì migration fail. Kiểm tra trước:
  ```sql
  SELECT transaction_id, COUNT(*) FROM orders
  WHERE transaction_id IS NOT NULL GROUP BY transaction_id HAVING COUNT(*) > 1;
  ```
- **Từ chối webhook thiếu chữ ký** khi đã bật secret → nếu gateway có lịch sử giao dịch cũ chưa gửi, có thể mất. Dùng `POST /api/payment/reconcile` để bù.
- **Unique index trên `transaction_id`** làm lỗi insert nếu giao dịch trùng — đã xử lý bằng check trước khi update; nếu vẫn lỗi → 500 → SePay retry → an toàn.
- `reconcile` quét toàn bộ giao dịch 3 ngày → payload lớn nếu shop bận rộn. Giới hạn `days` và có thể lọc theo số TK nhận (`account_number`) nếu cần.

## Câu hỏi còn mở

1. Cấu trúc mã thanh toán trên SePay có cấu hình prefix `ORD` trong dashboard để `code` = mã đơn không? Nếu không, `code` sẽ là `null` và phải dựa vào regex `content` (vẫn hoạt động nhờ đặt mã đơn trong nội dung CK).
2. SePay đang dùng gói nào (Free 50 giao dịch/tháng hay eShop)? Ảnh hưởng việc bật HMAC-SHA256 (một số gói chỉ hỗ trợ API Key) → cần xác nhận trước khi deploy.
3. Có bật chế độ "Chỉ gửi webhook khi giao dịch khớp mã thanh toán" không? Nếu có, mã đơn phải nằm đúng format cấu hình, nếu không webhook sẽ không tới.
4. Có cần hỗ trợ tài khoản ảo (VA) theo đơn không? Nếu có, `sub_account` sẽ là mã đơn → phải đổi regex `ORD\d+` thành mã định danh khác và thêm cột mapping.
5. Phase này có bật `AUTO_MIGRATE=true` trên production (Neon) không? Nếu không, migration phải chạy tay.
