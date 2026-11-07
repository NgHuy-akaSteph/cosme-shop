# Plan: Hoàn thiện tính năng biến thể (variants) cho sản phẩm

Ngày: 2026-11-07 · Work context: `/home/huyquang/Workspace/School/cosme-shop`
Phạm vi: BE validate + Admin UI quản lý variants + hiển thị order + seed + test.

## Bối cảnh

Rà soát toàn repo cho thấy variants đã có **hạ tầng đầy đủ** (DB JSONB, model, order flow, FE shop)
nhưng **admin không tạo/sửa được** sản phẩm có phân loại — tính năng không dùng được trên UI.
BE cũng **không validate** cấu trúc variants (`VariantInfo` define nhưng không dùng ở đâu).

## Phase

| Phase | Nội dung | Trạng thái |
|---|---|---|
| P1 | BE: validate `variants` bằng `VariantInfo` + `_normalize_variants` | ✅ Xong |
| P2 | FE: Admin UI quản lý variants (`Form.List`) | ✅ Xong |
| P3 | FE: sửa `OrderDetailPage` (type sai + thiếu cột "Phân loại") | ✅ Xong |
| P4 | BE: fix `RequestValidationError` handler crash khi lỗi custom | ✅ Xong |
| P5 | BE: test variants (11 case) | ✅ Xong |
| P6 | BE: seed 3 sản phẩm có variants | ✅ Xong |
| P7 | BE: gộp 2 nguồn stock → 1 nguồn sự thật | ✅ Xong |

## Chi tiết thay đổi

### P1 — BE validate (`app/schemas/product.py`)

- `VariantInfo`: thêm constraint `id`/`name` không rỗng, `price >= 0`, `stock >= 0`.
- `_normalize_variants()`: validate + chuẩn hóa thành dict JSON-safe.
  - `id` phải duy nhất trong 1 sản phẩm (cart key = `product_id + variant_id`).
  - `stock: null` → `0` (tránh `None < qty` khi order).
  - `price: null` → giữ `null` (FE fallback về `product.price`).
- Gắn `@field_validator("variants", mode="before")` vào `ProductCreate` + `ProductUpdate`.

### P2 — Admin UI (`frontend/src/pages/admin/Products.tsx`)

- Thêm `Form.List name="variants"`: bảng nhập ID / Tên / Giá / Stock + nút thêm-xoá.
- `normalizeVariants()`: bỏ dòng rỗng, tự sinh `id` (`v1`, `v2`…) nếu admin để trống hoặc id trùng.
- Cột "Biến thể" trong bảng danh sách (tag "N phân loại").
- Không có biến thể → gửi `variants: null` (không phải `[]`) để BE lưu `NULL`.

### P3 — Order detail user (`frontend/src/pages/user/OrderDetailPage.tsx`)

- Sửa type `variant_info` từ `{color?, size?}` (sai) → `{id?, name?}` (đúng snapshot BE).
- Thêm cột "Phân loại" vào bảng sản phẩm trong đơn.

### P4 — Fix handler validation (`app/main.py`)

Pydantic nhúng exception gốc vào `ctx["error"]` (vd `ValueError("ID biến thể bị trùng")`) →
`JSONResponse` ném `TypeError` thay vì trả 400. Thêm `_sanitize_validation_errors()` ép `ctx` về string.

> Đây là **latent bug** có sẵn từ trước, chỉ lộ ra khi có validator custom raise `ValueError`.

### P7 — Gộp 2 nguồn stock (`app/service/product_stock.py`)

Tạo module `app/service/product_stock.py` làm **nguồn sự thật duy nhất** cho logic stock:

| Trường hợp | Nguồn sự thật | `products.stock` |
|---|---|---|
| Không có variants | `products.stock` | giá trị admin nhập |
| Có variants | `variants[i].stock` | = **tổng** stock variants (dẫn xuất) |

Thay đổi:

- `order_service.create_order` — trừ **chỉ** `variants[i].stock`, rồi `recompute_stock()`.
  Trước đây trừ cả 2 nguồn → lệch nhau.
- `order_service.cancel_order` — hoàn vào `variants[i].stock` + `recompute_stock()`;
  chỉ hoàn thẳng vào `products.stock` khi không có biến thể.
- `product_service.create_product` / `update_product` — `recompute_stock()` sau khi gán.
- `api/products.py` + `api/wishlist.py` — trả `effective_stock(p)` (API luôn khớp tổng variants).
- `api/products.py` — sửa `price` variant: dùng `variant.get("price")` (tránh `v.get("price", ...)` trả `None` khi key tồn tại nhưng value `null`).
- **Chặn bán quá tồn kho**: sản phẩm có variants mà đơn không gửi `variant_id` → 400.
- `variant_id` gửi cho sản phẩm không có variants → 400 (trước đây pass im lặng).
- FE admin: field "Stock" **disabled** khi có biến thể + gửi `stock` = tổng variants.

### P8 — Fix `conftest.py` không so index (`tests/conftest.py`)

`metadata.create_all` **không** tạo thêm index vào bảng đã tồn tại (chỉ tạo bảng thiếu).
Schema test cũ thiếu index `uq_orders_transaction_id` → test bảo vệ unique index **PASS nham**.

Sửa `_drop_outdated_tables` so sánh cả **index** (`pg_indexes`) chứ không chỉ cột.

## Kết quả kiểm chứng

- `pytest backend/tests` → **126 passed** (baseline trước khi sửa: 91).
- `tsc -b` (frontend) → exit 0, không lỗi type.
- `eslint` (file đổi) → exit 0.
- Test mới `backend/tests/test_product_variants.py` — 11 case:
  - validate: tạo hợp lệ, thiếu `id`, `id` trùng, `price` âm, xoá hết → `null`.
  - order: tính giá theo variant, snapshot `variant_info`, variant không tồn tại → 400,
    hết stock variant → 400, trừ stock variant + product, hủy đơn hoàn stock.
- Test mới `backend/tests/test_product_stock.py` — 12 case:
  - helpers: tổng stock, null-safe, recompute ghi đè, giữ stock khi không có variants.
  - API: tạo/sửa sản phẩm → stock tự tính lại; `products.stock` cũ trong DB → API vẫn đúng.
  - order: chỉ trừ biến thể đã mua, biến thể khác không đổi; hủy đơn hoàn đúng;
    đơn thiếu `variant_id` → 400; `variant_id` trên sản phẩm không có variants → 400.

## Việc CHƯA làm (cần phase sau)

1. **Filter giá theo variant** — `min_price`/`max_price` dùng `products.price`, không dùng giá thấp nhất
   trong variants → lọc sai với sản phẩm có biến thể giá khác.
2. **Ảnh riêng cho từng variant** — schema có `image_url` nhưng admin UI chưa cho upload.
3. **Test FE** — chưa có test runner cho React trong project.
4. **`stats_service.low_stock`** — vẫn query theo `products.stock` cột (giờ là giá trị dẫn xuất nên
   vẫn đúng, nhưng chưa cân nhắc sắp hết hàng **theo từng biến thể**).

