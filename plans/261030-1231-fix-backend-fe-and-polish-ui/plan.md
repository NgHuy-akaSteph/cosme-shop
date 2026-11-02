# Plan: Sửa backend + cải thiện giao diện frontend (bỏ qua AI)

Ngày: 2026-10-30 · Work context: `/home/huyquang/Workspace/School/cosme-shop`
Phạm vi: sửa lỗi & bổ sung API backend, sau đó cải thiện giao diện FE. **Tạm bỏ qua toàn bộ tính năng AI.**

## Phase

| Phase | Nội dung | Trạng thái |
|---|---|---|
| [phase-01](phase-01-backend-bugfix.md) | Backend: sửa lỗi đếm user, filter OR, update null, sold_count, auth payment status | ✅ Hoàn thành |
| [phase-02](phase-02-backend-hardening.md) | Backend: webhook SePay, DRY serializer, validate đầu vào, admin stats API | ✅ Hoàn thành |
| [phase-03](phase-03-frontend-bugfix.md) | FE: error message, type dữ liệu, phân trang, cart/checkout | ✅ Hoàn thành |
| [phase-04](phase-04-frontend-ui-refactor.md) | FE: theme, ProductCard, trang chủ, danh sách SP, chi tiết SP | ✅ Hoàn thành |
| [phase-05](phase-05-admin-ui-and-polish.md) | Admin UI, git hygiene, docs, tests | ✅ Hoàn thành |
| [phase-06](phase-06-payment-sepay-hardening.md) | Payment SePay hardening: fix webhook camelCase, idempotent DB, HMAC-SHA256, reconcile API v2, tách lớp provider (hướng A) | ✅ Hoàn thành |

## Kết quả kiểm chứng (2026-10-31)

- Backend test suite (`backend/tests/`): **39/39 pass** — `TEST_DATABASE_URL` + `TEST_DATABASE_SCHEMA=cosme_test`.
- Frontend: `npm run build` exit 0, `npx eslint .` 0 lỗi (trước đó 38 lỗi `no-explicit-any`).
- Migration mới: `20261031_0900_c1d2e3f4a5b6_add_payment_webhook_logs.py`.

## Quyết định chiến lược thanh toán (đã chốt)

**Giữ SePay làm kênh chính.** payOS không triển khai ở giai đoạn hiện tại vì: không có sandbox (phải chuyển khoản thật để test), đổi hoàn toàn luồng thanh toán (redirect `checkoutUrl` thay vì QR nhúng), `orderCode` bắt buộc là integer (hiện là string `ORD...`), `description` giới hạn 9 ký tự (mã đơn hiện 15 ký tự), và cần migration DB. Ưu điểm của SePay: có Test mode (sandbox), dependency bằng 0, code đã xong.

Phase 06 thực hiện hướng A: vá lỗi mất tiền tiềm ẩn + siết bảo mật + tách lớp provider `app/payment/` để sau này cắm payOS chỉ cần thêm 1 file provider + đăng ký vào registry.

## Vấn đề cốt lõi đã xác nhận

Backend:
1. `GET /api/admin/users` trả `total = len(user_list)` → phân trang sai, Dashboard hiện "1 người dùng".
2. `GET /api/payment/status/{id}` không auth → ai cũng dò được đơn của người khác (IDOR).
3. Filter `skin_types`/`concerns` dùng AND, tài liệu yêu cầu OR.
4. `update_product` bỏ qua giá trị `None` → không xoá được `sale_price`.
5. `sold_count` không bao giờ tăng → "bán chạy" chỉ là dữ liệu seed.
6. Webhook SePay đánh dấu paid cho đơn đã cancelled; thiếu tiền chỉ log.
7. `_order_to_dict` copy-paste ở `orders.py` và `admin.py`; `order_service.py` import trùng.
8. Thiếu API thống kê cho dashboard.

Frontend:
9. 6 chỗ đọc `error.response?.data?.detail` trong khi backend trả `{message, code}` → thông báo lỗi không hiện.
10. `ProductDetailPage` khai báo `images: string[]` nhưng backend trả object → sai type.
11. 100% inline style, không có file CSS nào; `ProductCard` copy-paste 2 nơi.
12. Thiếu gallery, sản phẩm tương tự, filter theo loại da/vấn đề da.
13. Không có polling trạng thái thanh toán SePay.
14. `OrdersPage` lấy mặc định 20 đơn nhưng phân trang client-side.

Payment (phase-06):
15. Webhook SePay khai báo field snake_case nhưng payload thật là camelCase → `transfer_type` luôn `None` → đơn không bao giờ chuyển `paid`, trả success im lặng (mất tiền tiềm ẩn).
16. Không có idempotent ở mức DB, `transaction_id` không unique, không có log webhook → không đối soát/audit được.
17. Webhook chỉ xác thực API Key, không có HMAC-SHA256 → không chống giả mạo dữ liệu.
18. Nếu webhook không tới (tunnel chết) → đơn kẹt `unpaid` dù đã thu tiền, không có cơ chế đối soát.
19. Logic kiểm tra amount lệch với `docs/02-business-requirement.md` ("vẫn update" vs code "không update").
20. Business logic gắn cứng với SePay → chuyển sang payOS sau này phải viết lại.

## Ràng buộc

- Không đổi framework FE (giữ antd 5 + React 19).
- Không thêm template ngoài.
- Không dùng AI/LLM ở giai đoạn này.
- Mọi API mới phải khai báo trong `docs/03-tech-stack.md` và cập nhật `docs/02-business-requirement.md` nếu đổi nghiệp vụ.

## Liên kết

- Báo cáo đánh giá ban đầu: xem chat session hiện tại.
- UAT checklist hiện có: `plans/261013-0453-uat-readiness-fix/reports/uat-checklist.md`.
