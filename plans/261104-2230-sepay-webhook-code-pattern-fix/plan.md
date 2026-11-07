# Plan: Fix SePay webhook — mất tiền do lệch "mã thanh toán" + đối soát không quét được giao dịch

Ngày: 2026-11-04 · Work context: `/home/huyquang/Workspace/School/cosme-shop`
Phạm vi: backend SePay (QR, webhook, đối soát) + cấu hình dashboard SePay + docs + tests.

## Vấn đề gốc (đã xác minh bằng API thật SePay sandbox)

**P0 — Webhook sẽ KHÔNG được SePay gửi cho đơn của shop.**
Dashboard SePay đang cấu hình mẫu mã thanh toán tiền tố `COSME` + hậu tố 6–8 số, và webhook có
`prefix_filters: ["COSME"]` + `skip_if_no_code: true`. Nội dung chuyển khoản do shop sinh là
`SEVQR ORD202611042239` → không khớp mẫu `COSME` → SePay **bỏ qua giao dịch, không gọi webhook**
(tiền vào nhưng đơn kẹt `unpaid`). Mọi luồng trước đây "test được" vì giao dịch thử đều chứa
`COSME...` do người dùng tự nhập, không phải do QR của shop sinh ra.

**P1 — Đối soát không lấy được giao dịch nào.** `transaction_date_to` của SePay API v2 là **exclusive**
→ code hiện tại quét `from=hôm nay-3d, to=hôm nay` ⇒ trả về **0 giao dịch** (đã đo: 0 vs 2 khi +1 ngày).

**P2 — Schema chỉ nhận `id` kiểu int.** Webhook thật gửi `id: 44843` (int) nhưng API v2 trả `id` là UUID
string → `SePayWebhookPayload` reject UUID, và 2 nguồn ghi 2 `transaction_id` khác nhau cho cùng 1 giao dịch.

## Phase

| Phase | Nội dung | Trạng thái |
|---|---|---|
| [phase-01](phase-01-align-sepay-code-pattern.md) | Đồng bộ mã thanh toán SePay (dashboard) + validate order_code trong code | ✅ Xong (dashboard đã config) |
| [phase-02](phase-02-fix-reconcile-date-window.md) | Sửa cửa sổ ngày đối soát (exclusive `transaction_date_to`) | ✅ Xong |
| [phase-03](phase-03-harden-id-and-docs.md) | `transaction_id` int/str, tài liệu + checklist dashboard | ✅ Xong (dashboard đã config) |
| [phase-04](phase-04-tests-and-verify.md) | Test hồi quy + verify end-to-end với giao dịch thật | ✅ Xong (verify pass 2026-11-07) |

## Kết quả kiểm chứng (đã đạt)

- `pytest backend/tests/test_payment*.py` → **38 passed** (231s).
- SePay dashboard: 1 webhook `active`, `prefix_filters = ["ORD"]`, `skip_if_no_code = false`,
  mẫu mã `ORD` + hậu tố 12 số (Số nguyên) đang hoạt động, mẫu `COSME` đã ngưng.
- Giao dịch thật → SePay gọi webhook → HTTP **200** → `payment_webhook_logs.status = processed`
  → `orders.payment_status = paid`, `paid_at` khác null.
- `orders.transaction_id` = `reference_code` (`SB…`) — khoá chống trùng ổn định giữa webhook và đối soát.
- Đối soát: `scanned = 3` (trước khi fix = 0).

## Quyết định kiến trúc liên quan

Giữ nguyên `order_code = ORD + YYYYMMDD + 4 số` (đã có trong `docs/rules.md`, đã dùng ở FE/DB).
Không thêm cột `payment_code` mới — thay vào đó **cấu hình SePay theo format của shop** và
**validate trong code** để đổi format order_code về sau không âm thầm làm mất tiền (fail fast).

## Rủi ro / cần xác nhận từ user

1. ~~Truy cập dashboard SePay (my.sepay.vn) để đổi mẫu mã + `prefix_filters` + `skip_if_no_code`~~ — ✅ user đã làm (2026-11-07).
2. `ngrok` URL là URL tạm → mỗi lần đổi máy/đổi tunnel phải cập nhật lại `webhook_url` trên SePay.
   → Có thể cập nhật bằng `PUT /v2/webhooks/{id}` (đã dùng để đổi `prefix_filters`).
3. Nếu đổi mẫu mã sang `ORD` thì giao dịch cũ (nội dung `COSME...`) sẽ không còn `code` → chỉ ghi log `unmatched` (đã xử lý an toàn).
