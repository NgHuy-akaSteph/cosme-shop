# Plan: Rating dạng sao + đánh giá sản phẩm (Full)

Ngày: 2026-11-07 · Work context: `/home/huyquang/Workspace/School/cosme-shop`
Phạm vi: BE (bảng `reviews` + API + aggregate) + FE (UI sao, tab đánh giá, form viết) + seed + test + docs.

## Bối cảnh

Verify toàn repo: `products.rating_avg` / `rating_count` **đã có cột** từ migration initial schema
nhưng **chỉ là số liệu seed giả** (`backend/app/scripts/seed.py` — vd `4.5 / 89 lượt`).

- **Chưa có** bảng `reviews` trong `backend/app/model/` → không model/schema/service/API.
- **Chưa có** UI dạng sao: `frontend/src/pages/ProductDetailPage.tsx:150` in thẳng số thô;
  `frontend/src/components/ProductCard.tsx` không hiển thị gì.
- `backend/app/service/product_service.py` **không** đọc/ghi `rating_avg`; sort không có option rating.
- `@ant-design/icons` đã có sẵn `StarFilled`/`StarOutlined` → dựng component sao gần như miễn phí.

Kết luận: cần triển khai **full** (đã chốt với user: full + chỉ đơn `delivered` mới được đánh giá).

## Quyết định thiết kế (đã chốt)

- **1 đánh giá / user / sản phẩm** — `UniqueConstraint(user_id, product_id)` ở DB.
- **Điều kiện được đánh giá**: tồn tại `order_items` thuộc `orders` có `user_id = current_user`,
  `orders.status = 'delivered'`, `order_items.product_id = product_id`.
  Khớp đúng quy tắc tăng `sold_count` tại `backend/app/service/order_service.py:381`.
- **Aggregate** `rating_avg`/`rating_count` trên `products` là **derived cache**, tính lại từ
  `reviews` sau mỗi insert/update/delete. Không sửa tay.
- **Router riêng** `backend/app/api/reviews.py` (prefix `/api/reviews`) — `products.py` đã 288 dòng.
- **Seed**: bỏ số rating giả, thay bằng review thật gắn đơn `delivered`.

## Phase

| Phase | Nội dung | Trạng thái |
|---|---|---|
| [P1](phase-01-be-model-and-migration.md) | BE: model `reviews` + migration + đăng ký session | ⬜ Chưa làm |
| [P2](phase-02-be-schema-and-service.md) | BE: schema + service (verify purchased + recompute aggregate) | ⬜ Chưa làm |
| [P3](phase-03-be-api-and-sort.md) | BE: API `/api/reviews` + include router + sort `rating_desc` | ⬜ Chưa làm |
| [P4](phase-04-fe-rating-component-and-hooks.md) | FE: component sao + hook + types | ⬜ Chưa làm |
| [P5](phase-05-fe-ui-integration.md) | FE: ProductCard + ProductDetailPage + OrderDetailPage + sort option | ⬜ Chưa làm |
| [P6](phase-06-seed-tests-and-docs.md) | Seed + test + docs + verify | ⬜ Chưa làm |

## Dependency

```
P1 (model + migration)
  └─> P2 (schema + service)  ─┐
        └─> P3 (API)          ─┴─> P6 (seed + test + docs)
              └─> P4 (FE component + hook)
                    └─> P5 (FE tích hợp UI) ──> P6
```

P3 và P4 có thể làm song song sau P1/P2.

## Success Criteria (tổng)

- [ ] `pytest backend/tests` → tất cả pass (baseline hiện tại 102, không được giảm)
- [ ] `cd frontend && npx tsc -b` → exit 0
- [ ] `GET /api/products/{id}` → `rating_avg` khớp `AVG(reviews.rating)`, `rating_count` khớp `COUNT(*)`
- [ ] `GET /api/reviews/product/{id}` → list + `distribution` 1..5
- [ ] User có đơn `delivered` → POST review 201, `1 đánh giá / user / sản phẩm`
- [ ] User **chưa** mua → POST review 400 với message rõ ràng

## Rủi ro chung

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Migration trùng head | Cao | `down_revision = "f4a5b6c7d8e9"` (head hiện tại), kiểm tra `alembic heads` trước khi viết |
| Quên import model trong `db/session.py` → `create_all` không tạo bảng → test lỗi SQL | Cao | Bắt buộc import trong P1, verify bằng `Base.metadata.sorted_tables` |
| Race 2 request đánh giá đồng thời | Trung bình | `UniqueConstraint` ở DB + bắt `IntegrityError` → 400 |
| `order_items` chưa index theo `product_id` → query kiểm tra mua chậm khi data lớn | Thấp | Chấp nhận phase này, ghi follow-up |
| Xoá số rating seed giả → list hiển thị "Chưa có đánh giá" | Thấp | Seed review mẫu ở P6 |

## Câu hỏi còn mở

- Sort mặc định của trang list: giữ `newest`, chỉ thêm option `rating_desc` → **đã chốt**.
- Moderation (admin duyệt đánh giá): **không** làm ở phase này (YAGNI).
