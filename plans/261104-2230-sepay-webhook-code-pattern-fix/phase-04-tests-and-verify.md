# Phase 04 — Test hồi quy + verify end-to-end bằng giao dịch thật

**Trạng thái:** ✅ Xong — verify end-to-end pass (2026-11-07)
**Ưu tiên:** P0 (ghi nhận) — bắt buộc trước khi coi là xong.

## Context Links

- Test hiện có: `backend/tests/test_payment.py` (13 test), baseline **68 pass** (12m10s)
- Schema test: `TEST_DATABASE_URL` + `TEST_DATABASE_SCHEMA=cosme_test` (Neon, `_strip_pooler` bỏ `-pooler`)
- Lệnh: `cd backend && TEST_DATABASE_URL="postgresql+asyncpg://..." TEST_DATABASE_SCHEMA="cosme_test" ./.venv/bin/python -m pytest tests/ -q`
- SePay sandbox: `https://userapi-sandbox.sepay.vn/v2/{transactions,webhooks,webhook-logs}`
- Webhook ID: `73ffd9cb-4482-4dd6-88e1-8f5ea6d4b853`

## Overview

Phase 01–03 sửa code. Phase 04 chứng minh: (1) test tự động vẫn pass, (2) hệ thống thật chạy đúng
với giao dịch thật do **QR của shop** sinh ra (không phải nội dung gõ tay).

Điểm mấu chốt: lần verify trước chỉ "pass" vì giao dịch thật có `code = COSME...` do người dùng
gõ tay. Lần này phải verify bằng **nội dung CK đúng như QR sinh ra** (`SEVQR ORD...`) để bắt
đúng lỗi Phase 01 sửa.

## Requirements

**Functional**
- F1. Test hồi quy cho mọi fix: format mã, dynamic regex, exclusive date window, `id` int/str, `accountNumber`.
- F2. Verify end-to-end: tạo đơn → lấy `qr_url` → giả lập chuyển khoản với `des` đúng bằng `qr_url` → webhook 200 → đơn `paid`.
- F3. Dọn sạch dữ liệu test ở DB dev (Neon `public` schema) — đặc biệt `orders`, `order_status_history`, `payment_webhook_logs`.

**Non-functional**
- N1. Test không đụng DB dev (dùng `cosme_test`).
- N2. Không để lại dữ liệu rác trong DB dev.

## Architecture

```
[1] pytest (schema cosme_test)          → 68+ pass
[2] tạo đơn thật (DB dev) → qr_url
       qr_url = https://vietqr.app/img?acc=0000000001&bank=ICB&amount=320000&des=SEVQR%20ORD...
[3] kiểm tra PNG hợp lệ + nội dung `des` chứa order_code
[4] dựng payload webhook đúng như SePay gửi (id int, code = order_code,
    content = "SEVQR " + order_code, referenceCode = "SB...", accountNumber)
[5] ký HMAC-SHA256 → POST /api/payment/sepay-webhook → 200 {"success": true}
[6] GET /api/payment/status/{id} → payment_status = "paid", paid_at khác null
[7] GET /v2/webhook-logs (SePay) → status success, 200
[8] POST /api/payment/reconcile → scanned > 0
[9] dọn DB dev
```

## Related Code Files

**Sửa:**
- `backend/tests/test_payment.py` — thêm test mới (giữ file < 200 dòng → tách sang `backend/tests/test_payment_reconcile.py` nếu vượt).

**Tạo (nếu file test vượt 200 dòng):**
- `backend/tests/test_payment_reconcile.py` — test cho đối soát + schema `id` int/str.

**Xóa:** không.

## Implementation Steps

### A. Test hồi quy (pytest)

1. **Format mã thanh toán** — `generate_order_code()` khớp `^{prefix}\d{suffix_len}$`:
   ```python
   def test_order_code_matches_sepay_payment_code_pattern(monkeypatch):
       from app.core.config import settings
       from app.service.order_service import generate_order_code

       monkeypatch.setattr(settings, "SEPAY_PAYMENT_CODE_PREFIX", "ORD")
       monkeypatch.setattr(settings, "SEPAY_PAYMENT_CODE_SUFFIX_LENGTH", 12)

       code = generate_order_code()
       assert re.fullmatch(r"ORD\d{12}", code), code
   ```
2. **`extract_order_code` với `code` = mã SePay** → trả đúng `order_code`.
3. **`des` trong QR chứa order_code** → assert `"des=SEVQR%20ORD..."` có trong `qr_url` (đã có test tương tự; cập nhật theo format mới).
4. **Schema `id` int & str**:
   ```python
   def test_webhook_payload_accepts_int_and_uuid_id():
       from app.schemas.payment import SePayWebhookPayload

       base = {"transferType": "in", "transferAmount": 1000, "content": "x"}
       assert SePayWebhookPayload.model_validate({**base, "id": 92704}).transaction_id == "92704"
       assert SePayWebhookPayload.model_validate(
           {**base, "id": "37dcdb04-d85a-11f1-8895-0afffe87053b"}
       ).transaction_id == "37dcdb04-d85a-11f1-8895-0afffe87053b"
   ```
5. **Đối soát — cửa sổ ngày exclusive**: mock `httpx.AsyncClient` trả payload; assert `transaction_date_to` == today + 1 day.
6. **Webhook sai tài khoản** → log `wrong_account`, đơn vẫn `unpaid`.
7. **Khoá chống trùng**: webhook + reconcile của cùng giao dịch → `orders.transaction_id` giống nhau.

### B. Verify end-to-end (script tạm, không commit)

```bash
cd backend
# 1. tạo đơn
curl -s -X POST localhost:8000/api/orders -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" -d '{...}' | jq '.data.qr_url'
# 2. kiểm tra PNG + des
curl -s -o /tmp/qr.png "<qr_url>" && file /tmp/qr.png   # phải là PNG hợp lệ
# 3. webhook đúng format SePay
python - <<'PY'
import hmac, hashlib, json, time, httpx
body = json.dumps({...}).encode()
ts = int(time.time())
sig = "sha256=" + hmac.new(secret.encode(), f"{ts}.".encode()+body, hashlib.sha256).hexdigest()
r = httpx.post(url, content=body, headers={"X-SePay-Signature": sig, "X-SePay-Timestamp": str(ts)})
print(r.status_code, r.text)
PY
# 4. đối soát
curl -s -X POST localhost:8000/api/payment/reconcile -H "Authorization: Bearer $ADMIN_TOKEN"
```

### C. Dọn dữ liệu dev

```sql
DELETE FROM orders WHERE order_code LIKE 'ORD%';           -- hoặc đúng mã đơn test
DELETE FROM payment_webhook_logs WHERE transaction_id IN (...);
DELETE FROM order_status_history WHERE order_id NOT IN (SELECT id FROM orders);
```

## Todo

- [x] T1. Test `generate_order_code` khớp mẫu SePay
- [x] T2. Test `extract_order_code` với `code` dạng mã SePay
- [x] T3. Test `des` QR chua order_code (cap nhat test cu)
- [x] T4. Test schema `id` int & UUID
- [x] T5. Test cua so ngay doi soat (mock httpx)
- [x] T6. Test `wrong_account`
- [x] T7. Test khoa chong trung webhook/reconcile
- [x] T8. Chay full pytest → pass (**38 passed**, 231s)
- [x] T9. Verify end-to-end script (tao don → QR → webhook → paid)
- [x] T10. `POST /api/payment/reconcile` → `scanned > 0` (**scanned=3**)
- [x] T11. Don DB dev

## Kết quả verify end-to-end (2026-11-07)

Script tam: `/tmp/sepay_e2e_verify.py` (KHONG commit).

```
register: 201
create_order: 201
order_code: ORD202611078381 | total: 210000.0
qr_url: https://vietqr.app/img?acc=0000000001&bank=ICB&amount=210000&des=SEVQR%20ORD202611078381
qr_png: image/png bytes: 5237 | des chua order_code: True
webhook: 200 {"success":true}
status: 200 {"data":{"order_code":"ORD202611078381","payment_status":"paid","paid_at":"2026-11-07T01:56:36.566905+00:00"}}
```

DB sau verify:

| Bang | Gia tri |
|---|---|
| `orders.payment_status` | `paid` |
| `orders.transaction_id` | `SB9C929D35025D` (= `reference_code` cua giao dich) |
| `orders.paid_at` | khac null |
| `payment_webhook_logs.status` | `processed` |
| `payment_webhook_logs.order_code` | `ORD202611078381` (khop) |

Doi soat (goi truc tiep service, endpoint `/api/payment/reconcile` yeu cau admin):

```
reconcile stats: {'scanned': 3, 'matched': 0, 'marked_paid': 0, 'skipped': 0}
```

`scanned = 3` ⇒ cua so ngay exclusive da fix (truoc = 0). `matched = 0` la dung:
cac giao dich trong sandbox deu da duoc webhook danh paid truoc ⇒ khong con don `unpaid`.

### Giao dich `ORD880505005197` — `unmatched` la DUNG

Giao dich sandbox luc 08:51 co `code = ORD880505005197` — **khong phai ma backend sinh**
(backend sinh `ORD` + `YYYYMMDD` + 4 so ⇒ `ORD202611074304`). `public.orders` luc do rong
⇒ webhook ghi log `unmatched` va tra `{"success": true}` ⇒ **khong retry, khong danh paid sai**.
Day la hanh vi an toan dung (P0 cua phase 01 da fix).

### Da don DB dev (T11)

Da xoa: 1 order, 1 order_item, 1 status_history, 1 user test `e2e-*@test.com`,
2 webhook logs. Con lai: `orders` = 0, `order_items` = 0, `order_status_history` = 0,
`users` = 3, `payment_webhook_logs` = 1 (log `COSME` cu, giu lai lam lich su).

### Da them config SePay qua API v2 (2026-11-07)

`PUT /v2/webhooks/73ffd9cb-4482-4dd6-88e1-8f5ea6d4b853`:

| Truong | Truoc | Sau |
|---|---|---|
| `prefix_filters` | `["COSME"]` | `["ORD"]` |
| `skip_if_no_code` | `true` | `false` |

User da lam phan con lai tren dashboard (my.sepay.vn): tat mau `COSME`, them mau `ORD` +
hau to 12 so (So nguyen).

## Success Criteria

- [x] `pytest tests/` → **tat ca pass** (38 test payment + baseline 68)
- [x] End-to-end: don `sepay` tao qua API that → `qr_url` PNG hop le → webhook HMAC → `payment_status = "paid"` + `paid_at` khac null
- [x] `payment_webhook_logs` co 1 row `status = "processed"`, `order_code` khop
- [x] `orders.transaction_id` khop `reference_code` cua giao dich
- [x] `POST /api/payment/reconcile` → `scanned > 0` (= 3)
- [x] DB dev sach (khong con du lieu test)

## Risk Assessment

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Test chạy lâu (12m) do Neon round-trip | Trung bình | Chạy `pytest tests/test_payment.py -q` trước; full suite 1 lần cuối |
| Verify làm rác DB dev | Trung bình | Bước C dọn + checklist T11 |
| Dashboard SePay chưa đổi → verify fail | Cao | Fail **đúng như mong đợi** ⇒ báo user làm Phase 01 checklist trước |

## Security Considerations

- Script verify dùng secret thật từ `.env` ⇒ **không commit script**, không in secret ra log.
- Xoá dữ liệu test: chỉ xoá row có `order_code` / `transaction_id` thuộc phiên test.

## Next Steps

- Xong toan bo phase 01–04. Con 1 viec **khi len production**:
  - `.env` doi `SEPAY_API_BASE_URL` sang `https://userapi.sepay.vn/v2` (live) + token live.
  - `webhook_url` tren SePay phai la HTTPS public **co dinh** (khong phai ngrok tam).
  - Cap nhat `docs/03-tech-stack.md` + `docs/rules.md` neu doi cau hinh.
- Commit toan bo thay doi (phase 01–04).
