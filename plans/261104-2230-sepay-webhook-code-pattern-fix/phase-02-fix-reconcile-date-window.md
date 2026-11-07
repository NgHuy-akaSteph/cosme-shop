# Phase 02 — Sửa cửa sổ ngày đối soát (SePay `transaction_date_to` là exclusive)

**Trạng thái:** ✅ Xong
**Ưu tiên:** P1 — đối soát hiện không quét được giao dịch nào.

## Context Links

- Bằng chứng đo trực tiếp với SePay sandbox (`GET /v2/transactions`):
  ```
  from=2026-11-01, to=2026-11-04  → n=0   (code hiện tại)
  from=2026-11-01, to=2026-11-05  → n=2   (+1 ngày)
  from=2026-11-04, to=2026-11-04  → n=0   (from == to ⇒ rỗng)
  from=2026-11-04, to=2026-11-05  → n=2
  ```
- Code: `backend/app/service/payment_reconcile_service.py` (`fetch_recent_transactions`)
- Docs SePay: API v2 `/transactions`, params `transaction_date_from` / `transaction_date_to`

## Overview

**Vấn đề.** Code hiện tại:

```python
since = datetime.now(timezone.utc) - timedelta(days=days)
params = {
    "transaction_date_from": since.strftime("%Y-%m-%d"),
    "transaction_date_to": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    ...
}
```

SePay hiểu `transaction_date_to` là **exclusive** (không bao gồm ngày đó). Vì `from` và `to` đều là
hôm nay → cửa sổ rỗng ⇒ **luôn trả 0 giao dịch** ⇒ `POST /api/payment/reconcile` luôn báo
`scanned: 0`, tức cơ chế cứu vốn duy nhất khi webhook rớt **không bao giờ hoạt động**.

**Vì sao quan trọng.** Phase 01 sửa để webhook bắt đầu chạy đúng. Nhưng webhook vẫn có thể rớt
(mạng, server restart, SePay retry hết). Cơ chế đối soát là lưới an toàn thứ hai. Hiện lưới này
đang không có mắt.

**Quan trọng hơn:** khi Phase 01 áp dụng, giao dịch sẽ có `code` = `ORD...`; đối soát dựa vào
regex `ORD\d+` trong `transaction_content` — nhưng nội dung thật của giao dịch do shop sinh là
`SEVQR ORD202611042239` ⇒ regex vẫn khớp ✅. Còn với nội dung kiểu `SEVQR Thanh toan don hang COSME6246552`
(giao dịch tay) thì **không** khớp ⇒ cần fallback khớp `code` field của API v2 (đã có: `tx.get("code")`).

## Key Insights

- SePay so sánh ngày theo chuỗi `YYYY-MM-DD`, `transaction_date_to` exclusive.
- `days=3` hiện nghĩa là "3 ngày trước + hôm nay" — sau khi sửa thành "4 ngày" (hôm nay + 3 ngày trước). Chấp nhận: cửa sổ rộng hơn 1 ngày là an toàn (đối soát là best-effort, đã có idempotent).
- `transfer_type: "in"` đã thêm ✅ — API v2 trả cả `"out"` nếu không lọc.
- `per_page` mặc định 20; code đã đặt `per_page=100` + phân trang ✅ (giữ nguyên).
- `has_more` nằm ở `meta.pagination.has_more` ✅.

## Requirements

**Functional**
- F1. `transaction_date_to` = hôm nay + 1 ngày ⇒ luôn bao gồm giao dịch hôm nay.
- F2. `transaction_date_from` = hôm nay - `days` (giữ nguyên ý nghĩa "quét N ngày gần nhất").
- F3. Đối soát vẫn dùng `tx["code"]` **và** `tx["transaction_content"]` để tìm mã đơn (đã có, giữ).
- F4. Idempotent: chạy lại `reconcile` không đánh paid 2 lần (đã có ở `update_payment_status`).

**Non-functional**
- N1. Không hardcode số ngày; giữ tham số `days`.
- N2. Comment giải thích rõ "exclusive" để không ai "sửa lại" về hôm nay.

## Architecture

```
POST /api/payment/reconcile (admin)
        │
        ▼
fetch_recent_transactions(days=3)
        │  params = {
        │    transaction_date_from = today - 3 days   "2026-11-01"
        │    transaction_date_to   = today + 1 day     "2026-11-05"  ← exclusive ⇒ +1
        │    transfer_type = "in", per_page = 100
        │  }
        │  loop page 1..20, dừng khi meta.pagination.has_more == false
        ▼
reconcile_pending_orders(db)
        │  orders = sepay + unpaid + not cancelled
        │  for tx: match ORD\d+ trong f"{tx.code} {tx.transaction_content}"
        │  amount_in < total  → skipped (thiếu tiền)
        │  else update_payment_status(paid) + gắn transaction_id
        ▼
{"scanned": N, "matched": M, "marked_paid": K, "skipped": S}
```

## Related Code Files

**Sửa:**
- `backend/app/service/payment_reconcile_service.py` — `fetch_recent_transactions()`: cửa sổ ngày.
- `backend/app/service/payment_reconcile_service.py` — `reconcile_pending_orders()`: fallback match khi `code` không có `ORD\d+` (đối với giao dịch cũ `COSME...`).

**Tạo / Xóa:** không.

## Implementation Steps

1. **Sửa cửa sổ ngày** (`payment_reconcile_service.fetch_recent_transactions`):
   ```python
   now = datetime.now(timezone.utc)
   since = now - timedelta(days=days)
   # `transaction_date_to` cua SePay API v2 là EXCLUSIVE: giao dịch trong
   # chính ngày `to` KHÔNG được trả về. Phải +1 ngày để quét được giao
   # dịch hôm nay (nếu không, cửa sổ from==to ⇒ luôn rỗng).
   until = now + timedelta(days=1)
   params = {
       "transaction_date_from": since.strftime("%Y-%m-%d"),
       "transaction_date_to": until.strftime("%Y-%m-%d"),
       "transfer_type": "in",
       "per_page": PER_PAGE,
   }
   ```
2. **Thêm fallback match mã đơn**: hiện `ORDER_CODE_PATTERN = re.compile(r"ORD\d+")` — hardcode `ORD`.
   Phase 01 sẽ đổi sang dynamic pattern; ở phase này chỉ cần chắc chắn match trên `code` **và** `content`
   (đã có: `f"{code} {content}"`). Không cần sửa thêm — nhưng phải xác nhận lại sau phase 01.
3. **Verify bằng API thật**:
   ```bash
   curl -H "Authorization: Bearer $SEPAY_API_TOKEN" \
     "https://userapi-sandbox.sepay.vn/v2/transactions?transaction_date_from=<today-3>&transaction_date_to=<today+1>&transfer_type=in&per_page=100"
   ```
   → phải trả `total > 0`.
4. **Gọi endpoint thật**: `POST /api/payment/reconcile` (admin) → `scanned > 0`.

## Todo

- [x] T1. Sửa `transaction_date_to` = now + 1 day + comment giải thích
- [x] T2. Verify API thật trả `total > 0` với đúng params
- [x] T3. `fetch_recent_transactions()` thực tế → `scanned = 2` (trước khi sửa: `from==to` ⇒ 0)
- [x] T4. Test hồi quy: mock API trả 0 → `scanned == 0` không crash
- [x] T5. Test hồi quy: `days=0` vẫn quét được hôm nay (`from < to`)
- [x] T6. Test phân trang + lọc `transfer_type=in`
- [x] T7. Test đối soát: đơn khớp mã → paid; thiếu tiền → `skipped`; chạy lại → idempotent
- [ ] T8. `POST /api/payment/reconcile` trên server thật → `scanned > 0` (cần admin token + server chạy)

### Ghi chú triển khai

- Chỉ sửa `backend/app/service/payment_reconcile_service.py::fetch_recent_transactions`:
  ```python
  now = datetime.now(timezone.utc)
  since = now - timedelta(days=days)
  until = now + timedelta(days=1)   # transaction_date_to là EXCLUSIVE
  ```
- Bước 2 của phase (fallback match mã đơn) **đã được Phase 01 xử lý**:
  `payment_code_pattern()` dùng chung cho cả `tx["code"]` và `tx["transaction_content"]`.
- Test mới: `backend/tests/test_payment_reconcile.py` (6 test).
- Đo thực tế với sandbox SePay (2026-11-06):
  - `from=2026-11-06, to=2026-11-06` → `total=0` (xác nhận exclusive)
  - `from=2026-11-03, to=2026-11-06` → `total=2`
  - `from=2026-11-03, to=2026-11-07` → `total=2`
  - `fetch_recent_transactions(days=3)` sau sửa → **scanned = 2**

## Success Criteria

- [x] `fetch_recent_transactions()` trả về danh sách khác rỗng với dữ liệu sandbox hiện có (`scanned = 2`)
- [x] `fetch_recent_transactions()` dùng `transaction_date_to = hôm nay + 1 ngày` (exclusive)
- [x] Đơn `unpaid` có `code` khớp → chuyển `paid`; đơn thiếu tiền → `skipped` (test)
- [x] Chạy lại reconcile lần 2 → không đổi trạng thái (idempotent, test)
- [ ] `POST /api/payment/reconcile` trên server thật → `scanned > 0` (cần chạy server + admin token)

## Risk Assessment

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Cửa sổ rộng hơn 1 ngày → quét nhiều giao dịch cũ | Thấp | Chỉ đánh paid đơn `unpaid`; đã idempotent |
| Đối soát đánh paid nhầm đơn khi content trùng mã | Trung bình | Regex `ORD\d+` + kiểm tra `amount_in >= total` + unique `transaction_id` |

## Security Considerations

- Endpoint reconcile yêu cầu `get_current_admin` ✅ (đã có, test 401/403 sẵn).
- `SEPAY_API_TOKEN` chỉ dùng server-side, không lộ ra response.

## Next Steps

- Phase 03: `transaction_id` int/str + docs.
- Phase 04: test hồi quy + verify end-to-end.
