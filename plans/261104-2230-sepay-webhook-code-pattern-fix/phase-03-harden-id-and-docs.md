# Phase 03 — `transaction_id` int/str, đồng bộ 2 nguồn ID, docs + checklist dashboard

**Trạng thái:** ✅ Xong — dashboard đã config (2026-11-07), verify end-to-end pass
**Ưu tiên:** P2.

## Context Links

- Bằng chứng schema reject UUID:
  ```
  SePayWebhookPayload.model_validate({"id": 92704, ...})                              → OK
  SePayWebhookPayload.model_validate({"id": "37dcdb04-d85a-11f1-8895-...", ...})     → ValidationError: Input should be a valid integer
  ```
- Bằng chứng 2 nguồn ID khác nhau cho **cùng 1 giao dịch**:
  - Webhook payload thật: `{"id": 44843, "referenceCode": "SB2787C335AAF1", ...}`
  - API v2 cùng giao dịch: `{"id": "37dcdb04-d85a-11f1-8895-0afffe87053b", "reference_number": "SB2787C335AAF1", ...}`
  → `orders.transaction_id` sẽ nhận `44843` (từ webhook) hoặc `"37dcdb04-..."` (từ reconcile) ⇒
    **2 đơn khác nhau có thể cùng trỏ 1 giao dịch thật** ⇒ chống trùng bị vô hiệu.
- Code: `backend/app/schemas/payment.py`, `backend/app/service/payment_reconcile_service.py`, `backend/app/api/payment.py`
- Model: `backend/app/model/order.py` (`transaction_id: String(64)`), `backend/app/model/payment_webhook_log.py`

## Overview

**Vấn đề 1 — Schema quá chặt.** `SePayWebhookPayload.transaction_id: int = Field(..., alias="id")`.
Tài liệu webhook ghi `id` là integer ✅, nhưng:
- API v2 (`/v2/transactions`) trả `id` là **UUID string**.
- Nếu sau này dùng payload API v2 làm nguồn chuẩn (hoặc webhook đổi format), schema vỡ → 401.

**Vấn đề 2 — 2 nguồn ID không khớp.** Cùng 1 giao dịch thật:
- webhook → `id = 44843` (int), `referenceCode = SB2787C335AAF1`
- API v2 → `id = 37dcdb04-...` (UUID), `reference_number = SB2787C335AAF1`

`orders.transaction_id` + unique index `uq_orders_transaction_id` được thiết kế để chặn "1 giao dịch
đánh paid 2 đơn". Nhưng vì 2 nguồn sinh ID khác nhau, chống trùng **không hoạt động**:
- webhook đánh paid đơn A với `44843`
- reconcile đối chiếu giao dịch cùng đó → ghi `37dcdb04-...` cho đơn B ⇒ 2 đơn paid từ 1 giao dịch.

**Vấn đề 3 — Webhook trả 200 cho giao dịch không khớp.** Hiện đã trả `{"success": true}` + log
`unmatched` → đúng (tránh retry vô ích). Nhưng **thiếu validate số tài khoản nhận**: webhook
đang nhận mọi giao dịch "in" của tài khoản đã cấu hình ở SePay — nếu sau này dùng chung tài khoản
cho nhiều shop, giao dịch của shop khác sẽ lọt vào (dù đã `unmatched`).
→ Bổ sung check `accountNumber` khớp `SEPAY_BANK_ACCOUNT` (nếu cấu hình) ⇒ log `wrong_account`.

## Key Insights

- `referenceCode` / `reference_number` là **mã tham chiếu từ ngân hàng** ⇒ **ổn định giữa 2 nguồn** ⇒ dùng làm khoá chống trùng liên nguồn.
- `transaction_id` trong DB là `String(64)` — chứa được cả int lẫn UUID ✅ (không cần migration).
- `payment_webhook_logs.transaction_id` cũng `String(64)` ✅, unique `(provider, transaction_id)`.
- Webhook thật của SePay đã gửi `subAccount: ""` và `code` theo mẫu — dùng `code` làm khoá chính sẽ ổn định hơn `id`.
- SePay yêu cầu phản hồi `{"success": true}` + HTTP 200 trong 30s ✅ (đã đúng).

## Requirements

**Functional**
- F1. `SePayWebhookPayload.transaction_id` nhận được cả `int` và `str` (UUID).
- F2. `orders.transaction_id` lưu khoá chống trùng **ổn định giữa webhook và đối soát**.
- F3. Webhook: giao dịch `accountNumber` ≠ `SEPAY_BANK_ACCOUNT` ⇒ log `wrong_account`, **không** đánh paid.
- F4. `extract_order_code()` ưu tiên `code` (mã SePay trích) rồi mới tới `content`.

**Non-functional**
- N1. `transaction_id` trong DB phải là 1 giá trị duy nhất cho 1 giao dịch thật, bất kể nguồn.
- N2. Không thêm bảng/cột mới (YAGNI) — dùng `reference_code` làm khoá chính.

## Architecture

```
Webhook (id=44843, referenceCode=SB2787C335AAF1) ─┐
                                                  ├─→ khoá chống trùng = reference_code
API v2   (id=37dcdb04-..., reference_number=SB2787C335AAF1) ─┘
                                                        (fallback: id nếu không có reference)
```

Chọn `reference_code` làm `orders.transaction_id`:
- Ổn định giữa 2 nguồn ⇒ chống trùng thật sự hoạt động.
- `referenceCode` từ ngân hàng (VD `SB2787C335AAF1`, `FT24012345678`) — không rỗng trong thực tế.
- Nếu rỗng → fallback `str(id)` (hành vi hiện tại, không làm hỏng gì).

## Related Code Files

**Sửa:**
- `backend/app/schemas/payment.py` — `transaction_id: str` (nhận int & str), thêm `reference_code` đã có.
- `backend/app/service/order_service.py` — `update_payment_status()`: nhận `transaction_id` đã chuẩn hoá.
- `backend/app/service/payment_reconcile_service.py` — dùng `reference_number` (fallback `id`) làm transaction_id.
- `backend/app/api/payment.py` — validate `accountNumber`; dùng `reference_code` làm khoá.
- `backend/app/payment/sepay_provider.py` — `extract_order_code()` ưu tiên `code`.

**Tạo / Xóa:** không.

## Implementation Steps

1. **Schema** (`backend/app/schemas/payment.py`):
   ```python
   # `id` là khóa chống trùng. Tài liệu webhook ghi là integer, nhưng API v2
   # trả UUID string → chấp nhận cả hai, chuẩn hoá về str.
   transaction_id: str = Field(..., alias="id")

   @field_validator("transaction_id", mode="before")
   @classmethod
   def _coerce_tx_id(cls, v: Any) -> str:
       return str(v)
   ```
   Kiểm tra `transferAmount`/`accumulated` cũng nên nhận str→int (SePay có thể gửi số dạng chuỗi) — dùng `Field(..., alias=...)` + `BeforeValidator`.
2. **Tạo helper khoá chống trùng** (1 nguồn sự thật) — đặt trong `sepay_provider.py` hoặc `payment_security_service.py`:
   ```python
   def build_transaction_key(*, reference_code: str | None, transaction_id: Any) -> str:
       """Khoá chống trùng ổn định giữa webhook và đối soát."""
       if reference_code:
           return str(reference_code)
       return str(transaction_id)
   ```
3. **Webhook** (`backend/app/api/payment.py`):
   - `transaction_id = provider.build_transaction_key(...)` dùng cho log + `orders.transaction_id`.
   - Validate `accountNumber`:
     ```python
     if settings.SEPAY_BANK_ACCOUNT and payload.account_number and \
        payload.account_number != settings.SEPAY_BANK_ACCOUNT:
         _mark_webhook_status(log_row, "wrong_account")
         await db.commit()
         return {"success": True}
     ```
4. **Đối soát** (`payment_reconcile_service.reconcile_pending_orders`):
   ```python
   tx_key = build_transaction_key(
       reference_code=tx.get("reference_number"),
       transaction_id=tx.get("id"),
   )
   await order_service.update_payment_status(db, order_code=order_code, transaction_id=tx_key)
   ```
5. **`extract_order_code`** (`sepay_provider.py`): hiện ưu tiên `payload.code` → `sub_account` → `content` ✅ đúng thứ tự rồi. Chỉ cần đảm bảo `code` là mã SePay trích (ORD...) — phase 01 lo.
6. **Docs:** cập nhật `docs/01-system-design.md` (§6.3 webhook), `docs/rules.md`, `docs/03-tech-stack.md`.

## Todo

- [x] T1. Schema `transaction_id` nhận int & str (+ `BeforeValidator` cho amount nếu cần)
- [x] T2. Helper `build_transaction_key` (1 nguồn sự thật)
- [x] T3. Webhook dùng khoá `reference_code` cho log + `orders.transaction_id`
- [x] T4. Webhook validate `accountNumber` → `wrong_account`
- [x] T5. Đối soát dùng cùng khoá
- [x] T6. Docs đồng bộ (`01-system-design.md`, `rules.md`, `02-business-requirement.md`, `04-database.md`)
- [x] T7. Kiểm tra endpoint đọc `payment_webhook_logs` không lộ payload ra public → **không có endpoint đọc log** (`payment_webhook_logs` chỉ được ghi, không có API đọc) ⇒ không rò rỉ `description` (tên người chuyển)
- [x] T8. **User**: checklist dashboard SePay (phase 01) + verify end-to-end (phase 04) — ✅ 2026-11-07

### Ghi chú triển khai

- Tạo `backend/app/payment/transaction_key.py` — helper `build_transaction_key(reference_code, transaction_id)`,
  ưu tiên `reference_code`, fallback `str(transaction_id)`.
- `backend/app/schemas/payment.py`:
  - `transaction_id: str` + `field_validator(mode="before")` → nhận int (webhook) và UUID (API v2).
  - `amount_in` / `accumulated` ép `str` → `int` (SePay có thể gửi số dạng chuỗi).
- `backend/app/api/payment.py`:
  - `transaction_id = build_transaction_key(reference_code=payload.reference_code, transaction_id=payload.transaction_id)`.
  - Thêm check `accountNumber` ≠ `SEPAY_BANK_ACCOUNT` → log `wrong_account`, KHÔNG đánh paid.
    So sánh đã **bỏ số 0 đầu** (`_normalize_account`) vì ngân hàng có thể gửi `1` thay vì `0000000001`.
- `backend/app/service/payment_reconcile_service.py`: dùng `build_transaction_key(reference_code=tx["reference_number"], transaction_id=tx["id"])`.
- **Không cần migration DB** — `transaction_id` đã là `String(64)`, chứa được cả `SB2787C335AAF1` lẫn UUID.
- Test mới: `backend/tests/test_payment_transaction_key.py` (9 test).
- Cập nhật `backend/tests/test_payment.py`: fixture `_sepay_secret` set `SEPAY_BANK_ACCOUNT`
  khớp `accountNumber` của payload giả (`1017588888`) — nếu không, 2 test cũ fail do check tài khoản mới.
- Đo thực tế sandbox (2026-11-06): API v2 trả `id = "37dcdb04-d85a-11f1-8895-0afffe87053b"`,
  `reference_number = "SB2787C335AAF1"`, `account_number = "0000000001"`.

## Success Criteria

- [x] `model_validate({"id": 92704, ...})` OK
- [x] `model_validate({"id": "37dcdb04-...", ...})` OK
- [x] Webhook + reconcile của cùng 1 giao dịch → cùng 1 `orders.transaction_id` (= `reference_code`)
- [x] Giao dịch sai tài khoản → log `wrong_account`, đơn vẫn `unpaid`
- [x] Không cần migration DB

## Risk Assessment

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Đổi khoá sang `reference_code` → giao dịch đã ghi `id` cũ bị lệch | Thấp | Đây là hệ thống dev, dữ liệu cũ đã dọn; unique index chỉ áp dụng giá trị mới |
| `referenceCode` rỗng ở 1 số ngân hàng | Thấp | Fallback `str(id)` |

## Security Considerations

- `payload` trong `payment_webhook_logs` chứa `description` (tên người chuyển) — nếu có endpoint admin đọc log, phải giới hạn admin.
- Thêm check `accountNumber` giảm bề mặt tấn công "gửi webhook giả từ tài khoản khác" (dù HMAC đã chặn).

## Next Steps

- Phase 04: test hồi quy + verify end-to-end — ✅ xong 2026-11-07 (38 test pass, E2E `paid`).
- Còn: chuyển `.env` sang SePay **live** + `webhook_url` HTTPS public cố định khi lên production.
