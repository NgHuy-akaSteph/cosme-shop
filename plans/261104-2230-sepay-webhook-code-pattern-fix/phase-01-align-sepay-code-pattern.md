# Phase 01 — Đồng bộ "mã thanh toán" SePay với order_code của shop

**Trạng thái:** ✅ Xong — dashboard đã config (2026-11-07), verify end-to-end pass
**Ưu tiên:** P0 — đang làm mất tiền thật.

## Context Links

- Bằng chứng: `GET https://userapi-sandbox.sepay.vn/v2/webhooks/{id}` → `prefix_filters: ["COSME"]`, `skip_if_no_code: true`
- Bằng chứng: `GET /v2/webhook-logs` → 2 giao dịch `status: failed`, `response_status_code: 401` (lúc đó secret cũ), `replayable: true`
- Bằng chứng: `POST /v2/webhook-logs/{tx}/replay` → 200 `delivered: true` → log mới `status: success, 200`
- Bằng chứng payload thật lưu ở `payment_webhook_logs.payload`:
  ```json
  {"id": 44843, "code": "COSME6246552", "content": "SEVQR Thanh toan don hang COSME6246552",
   "transferType": "in", "transferAmount": 200000, "accountNumber": "0000000001"}
  ```
- Docs SePay: [Cấu hình mã thanh toán](https://developer.sepay.vn/vi/sepay-webhooks/cau-hinh-ma-thanh-toan), [Tạo webhook](https://developer.sepay.vn/vi/sepay-webhooks/tao-webhook)
- Code liên quan: `backend/app/payment/sepay_provider.py`, `backend/app/service/order_service.py` (`generate_order_code`), `backend/app/schemas/order.py`

## Overview

**Vấn đề.** SePay bóc tách `code` từ nội dung chuyển khoản theo *mẫu mã thanh toán* khai báo ở
Công ty → Cấu hình chung. Mẫu đang khai báo: tiền tố `COSME`, hậu tố 6–8 ký tự số. QR của shop sinh
nội dung `SEVQR ORD202611042239` → **không khớp mẫu nào** → `code = null`.

Hệ quả trực tiếp (kết hợp với webhook config):
- `skip_if_no_code: true` ⇒ SePay **không gửi webhook** cho giao dịch đó.
- `prefix_filters: ["COSME"]` ⇒ chỉ gửi khi `code` bắt đầu bằng `COSME` — vẫn loại.
- Kết quả: tiền vào tài khoản, đơn hàng **kẹt `unpaid`** vô hạn, không có log để đối chiếu.

Đây là lỗi "silent money loss": mọi test cũ đều pass vì test webhook **tự dựng payload** có `code`
là `ORD...`, và test giao dịch thật thì người dùng gõ tay `COSME...` trong nội dung — không phải
QR của shop sinh ra.

**Nguyên nhân gốc:** hai hệ thống dùng hai "ngôn ngữ" mã khác nhau —
SePay: `COSME` + 6–8 số. Shop: `ORD` + `YYYYMMDD` + 4 số (`ORD202611042239` = 15 ký tự).

## Key Insights

- SePay **chỉ match mẫu đầu tiên** và dừng; mẫu phải khớp `<tiền tố><hậu tố>` liên tiếp trong nội dung.
- Tiền tố hợp lệ: 2–5 ký tự. Hậu tố: 1–30 ký tự. Loại ký tự: `Số nguyên` hoặc `Số và chữ`.
- `ORD202611042239` hậu tố = `202611042239` = 12 ký tự số → **hợp lệ** với khoảng hậu tố 12–12 (hoặc 11–13 để linh hoạt).
  Nhưng nếu hậu tố là "Số và chữ" thì `ORD202611042239` vẫn khớp vì `202611042239` toàn số.
- Chọn hậu tố **cố định 12** để `code` luôn = toàn bộ `order_code` → backend so khớp chắc chắn.
  Nếu để khoảng rộng (6–30) mà nội dung chứa thêm chữ số phía sau, `code` có thể bị cắt.
- `SEVQR` prefix trong nội dung CK là yêu cầu của **VietinBank cá nhân** (đã cấu hình `SEPAY_QR_CONTENT_PREFIX=SEVQR`).
  Nó **không** phải mã thanh toán — SePay quét toàn bộ nội dung nên vẫn tìm thấy `ORD...` sau nó.
- `prefix_filters` phải chứa tiền tố của mẫu mã (`ORD`), không phải `SEVQR`.

## Requirements

**Functional**
- F1. Mẫu mã thanh toán SePay = tiền tố `ORD`, hậu tố 12 ký tự số → `code` = `ORD202611042239`.
- F2. Webhook: `prefix_filters = ["ORD"]`, `skip_if_no_code = false` (để giao dịch không có mã vẫn tới server và được ghi log `unmatched` — an toàn hơn là bị SePay âm thầm bỏ).
- F3. Backend tự validate `order_code` đúng format SePay sẽ trích, fail-fast nếu lệch.
- F4. `SEPAY_QR_CONTENT_PREFIX` không được nuốt mất `order_code` khi `des` bị ngân hàng cắt bớt.

**Non-functional**
- N1. Không hardcode prefix `ORD` rải rác — 1 nguồn sự thật duy nhất.
- N2. Đổi format `order_code` sau này chỉ cần sửa 1 chỗ + cập nhật mẫu SePay.
- N3. Không log số tiền/chi tiết người dùng vào log không mã hoá.

## Architecture

```
┌─ QR sinh ra (shop) ────────────────────────────────┐
│ sepay_provider._build_transfer_content(order_code)  │
│   → "SEVQR ORD202611042239"                         │
└──────────────────────┬───────────────────────────────┘
                       │ nội dung CK
                       ▼
┌─ Ngân hàng ─────────────────────────────────────────┐
│ VietinBank: giữ nguyên nội dung                     │
└──────────────────────┬───────────────────────────────┘
                       ▼
┌─ SePay ──────────────────────────────────────────────┐
│ Quét nội dung theo mẫu đang active:                 │
│   mẫu "ORD" + hậu tố 12 số  → code = ORD202611042239 │
│   (mẫu "COSME" cũ → không khớp, bị bỏ qua)          │
└──────────────────────┬───────────────────────────────┘
                       │ POST webhook (HMAC)
                       ▼
┌─ Backend /api/payment/sepay-webhook ─────────────────┐
│ payload.code = "ORD202611042239"                     │
│ extract_order_code() → khớp order trong DB           │
└──────────────────────────────────────────────────────┘
```

## Related Code Files

**Sửa:**
- `backend/app/service/order_service.py` — `generate_order_code()`: sinh mã theo format SePay biết (prefix + hậu tố cố định).
- `backend/app/payment/sepay_provider.py` — `_build_transfer_content()`: tách prefix bắt buộc của ngân hàng (`SEVQR`) khỏi mã thanh toán.
- `backend/app/core/config.py` — thêm `SEPAY_PAYMENT_CODE_PREFIX` (mặc định `ORD`) + `SEPAY_PAYMENT_CODE_SUFFIX_LENGTH` (mặc định `12`).

**Tạo:** không tạo file mới (YAGNI) — chỉ sửa file hiện có.

**Xóa:** không.

## Implementation Steps

1. **Thêm config** (`backend/app/core/config.py`):
   ```python
   # Mã thanh toán SePay: tiền tố + hậu tố cố định, phải KHỚP với mẫu mã
   # khai báo ở SePay dashboard (Công ty → Cấu hình chung → Cấu trúc mã thanh toán).
   SEPAY_PAYMENT_CODE_PREFIX: str = "ORD"
   SEPAY_PAYMENT_CODE_SUFFIX_LENGTH: int = 12
   ```
2. **Sinh `order_code` đúng format** (`order_service.generate_order_code`):
   ```python
   def generate_order_code() -> str:
       """ORD + YYYYMMDD + 4 số random -> hậu tố 12 ký tự số, khớp mẫu mã SePay."""
       prefix = settings.SEPAY_PAYMENT_CODE_PREFIX.strip().upper()
       suffix_len = settings.SEPAY_PAYMENT_CODE_SUFFIX_LENGTH
       body = datetime.now(timezone.utc).strftime("%Y%m%d") + str(random.randint(1000, 9999))
       return f"{prefix}{body}"[:prefix_len + suffix_len]
   ```
   > Phải đảm bảo `len(order_code) == len(prefix) + suffix_len` và phần hậu tố **toàn số**.
3. **Tách 2 loại prefix trong nội dung CK** (`sepay_provider._build_transfer_content`):
   - `SEPAY_QR_CONTENT_PREFIX` (`SEVQR`) = yêu cầu ngân hàng → giữ nguyên trong `des`.
   - `SEPAY_PAYMENT_CODE_PREFIX` (`ORD`) = mã thanh toán SePay → nằm trong `order_code` (đã có sẵn).
   - Kiểm tra: `des` phải chứa `order_code` (không bị cắt). Nếu `SEPAY_QR_CONTENT_PREFIX` rỗng → `des = order_code`.
4. **Fail-fast validate** (`sepay_provider.create_payment_link` hoặc helper riêng): nếu `order_code` **không** khớp regex `^{prefix}\d{suffix_len}$` → raise/log lỗi nghiêm trọng, **không** trả QR sai (QR sai ⇒ mất tiền).
5. **Sửa regex extract order code** (`sepay_provider.ORDER_CODE_PATTERN`): hiện là `re.compile(r"ORD\d+")` — hardcode `ORD`. Đổi sang động theo config, hoặc giữ `ORD\d+` + thêm fallback. → dùng dynamic pattern dựng từ `settings.SEPAY_PAYMENT_CODE_PREFIX`.
6. **Cập nhật `.env` + `.env.example`**: `SEPAY_PAYMENT_CODE_PREFIX=ORD`, `SEPAY_PAYMENT_CODE_SUFFIX_LENGTH=12`.
7. **Cập nhật `docs/rules.md`** (§ order code format) và `docs/01-system-design.md` (§6.3.1 QR VietQR).

## Todo

- [x] T1. Thêm `SEPAY_PAYMENT_CODE_PREFIX` + `SEPAY_PAYMENT_CODE_SUFFIX_LENGTH` vào `config.py`
- [x] T2. `generate_order_code()` sinh mã đúng format (prefix + hậu tố số cố định)
- [x] T3. `_build_transfer_content()` tách prefix ngân hàng vs prefix mã thanh toán
- [x] T4. Dynamic `ORDER_CODE_PATTERN` theo config (2 nơi dùng: `sepay_provider.py`, `payment_reconcile_service.py`)
- [x] T5. Fail-fast validate format mã trước khi sinh QR
- [x] T6. `.env` + `.env.example` cập nhật
- [x] T7. Docs `rules.md` + `01-system-design.md` + `03-tech-stack.md` + `02-business-requirement.md` + `04-database.md`
- [x] T8. **User**: làm checklist dashboard SePay (bên dưới) — ✅ đã làm 2026-11-07
- [x] T9. Verify end-to-end (phase 04) — ✅ pass 2026-11-07

### Ghi chú triển khai

- Nguồn sự thật duy nhất: `backend/app/payment/payment_code.py`
  (`payment_code_prefix`, `payment_code_suffix_length`, `payment_code_pattern`,
  `is_valid_payment_code`, `validate_payment_code`, `build_payment_code`).
- `sepay_provider.ORDER_CODE_PATTERN` và `payment_reconcile_service.ORDER_CODE_PATTERN`
  (hardcode `ORD\d+`) đã bị **xoá**, thay bằng `payment_code_pattern()` dựng động từ config.
- `create_payment_link` raise `ValueError` khi mã không khớp; `order_service.create_order`
  và `api/orders._build_sepay_qr_url` bắt lỗi này → log + `qr_url = None` (không trả QR sai).
- Test mới: `backend/tests/test_payment_code.py` (8 test).

## Success Criteria

- [x] `generate_order_code()` luôn trả về `ORD` + 12 số, khớp regex mẫu SePay
- [x] `des` trong QR chứa đúng `order_code` (đã kiểm chứng `vietqr.app/img` trả PNG 360x360 hợp lệ)
- [x] `extract_order_code(payload)` với `code="ORD202611042239"` → trả `"ORD202611042239"`
- [x] Đổi `SEPAY_PAYMENT_CODE_PREFIX` trong `.env` → không cần sửa code khác
- [x] `pytest backend/tests` → **76 passed** (68 baseline + 8 test mới)
- [x] Checklist dashboard SePay hoàn tất (xem bên dưới) — **user đã làm 2026-11-07**
  - `prefix_filters` + `skip_if_no_code` đã đổi tự động qua `PUT /v2/webhooks/{id}` (API v2).
  - Mẫu mã `COSME` đã ngưng, mẫu `ORD` + hậu tố 12 số (Số nguyên) đang hoạt động (user làm trên dashboard).

## Checklist dashboard SePay (user thực hiện thủ công)

1. **Công ty → Cấu hình chung → Cấu trúc mã thanh toán**
   - Sửa mẫu `COSME` (hậu tố 6–8 số) → **mẫu `ORD`, hậu tố 12, loại ký tự: Số nguyên**, trạng thái *Đang hoạt động*.
   - Xoá / ngưng hoạt động mẫu `COSME` (nếu còn) để tránh match sai.
2. **Webhooks → "Xác thực thanh toán"**
   - `prefix_filters`: `["ORD"]` (bỏ `COSME`)
   - `skip_if_no_code`: **false** (để giao dịch lạ vẫn tới server, được log `unmatched`)
   - `event_type`: `In_only` ✅, `authen_type`: `HMAC_SHA256` ✅, `active`: true ✅
   - `webhook_url`: `https://<public-domain>/api/payment/sepay-webhook` — **phải là HTTPS public**, ngrok tạm thì sẽ phải cập nhật lại khi đổi tunnel.
3. **Xác minh:** vào `Lịch sử gửi` (webhook logs) sau khi chuyển khoản thật → status `success`, response `200`.

## Risk Assessment

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Quên đổi mẫu mã trên dashboard → vẫn mất tiền | Cao | Phase 04 verify end-to-end bằng giao dịch thật + `POST /api/payment/reconcile` phải thấy giao dịch |
| Đổi mẫu mã làm giao dịch cũ (`COSME...`) mất `code` | Thấp | Backend đã log `unmatched` + trả `{"success": true}` ⇒ SePay không retry vô ích; đối soát API v2 vẫn thấy (nếu content chứa `ORD...`) |
| Hậu tố 12 cố định làm `order_code` dài hơn hiện tại | Thấp | `orders.order_code` là `String(32)` → 15 ký tự vẫn vừa |
| Regex dynamic theo config → sai khi config lệch | Thấp | Validate + test |

## Security Considerations

- **Auth:** webhook giữ HMAC-SHA256 (`SEPAY_WEBHOOK_SECRET`), timestamp chống replay (±300s) — không đổi.
- **Data protection:** `payment_webhook_logs.payload` lưu nguyên payload SePay (chứa tên người chuyển ở `description`) → cần đảm bảo endpoint admin đọc log không lộ ra public. Kiểm tra lại khi làm phase 03.
- **Fail-safe:** khi format mã sai → **không** sinh QR (chặn mất tiền), log cảnh báo rõ ràng.

## Next Steps

- Phase 02: sửa cửa sổ ngày đối soát.
- Phase 03: `transaction_id` int/str + docs.
- Phase 04: test hồi quy + verify end-to-end.
