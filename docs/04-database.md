# Database — cosme-shop

Tài liệu này mô tả chi tiết database của hệ thống `cosme-shop`: cấu hình kết nối, sơ đồ quan hệ, schema từng bảng, cấu trúc JSON columns, indexes, quy tắc ràng buộc, migration Alembic, code organization và vấn đề hiện tại cần xử lý.

Tài liệu liên quan:

- [01-system-design.md](01-system-design.md) — kiến trúc tổng thể, luồng nghiệp vụ.
- [02-business-requirement.md](02-business-requirement.md) — nghiệp vụ theo vai trò.
- [03-tech-stack.md](03-tech-stack.md) — dependencies, biến môi trường, ports.
- [rules.md](rules.md) — quy tắc code & quy tắc DB.

## 1. Tổng quan

- **Database engine:** PostgreSQL 17 (image `postgres:17-alpine`, port `5432`).
- **Driver:** `asyncpg` (async).
- **ORM:** SQLAlchemy 2.x async + Alembic migration.
- **Schema duy nhất:** `public` (đã loại bỏ schema `ai`).
- **Tên database:** `cosme_shop`.
- **Số bảng MVP:** 9 bảng nghiệp vụ.
- **KHÔNG dùng** extension `pgvector` (đã loại bỏ — AI gọi Gemini API trực tiếp, không có embedding).
- **DB GUI dev:** Adminer ở port `8080`.

## 2. Sơ đồ quan hệ (ERD)

```mermaid
erDiagram
    users ||--o{ orders : "dat hang"
    users ||--o{ wishlists : "yeu thich"
    users ||--o{ order_status_history : "ghi nhan"

    orders ||--|{ order_items : "chua"
    orders ||--o{ order_status_history : "lich su"

    categories ||--o{ products : "gom"
    brands ||--o{ products : "thuong hieu"
    products ||--o{ order_items : "snapshot"
    products ||--o{ wishlists : "yeu thich"

    payment_webhook_logs {
        int id PK
        string provider
        string transaction_id UK
        string order_code
        int amount
        json payload
        string status
        text error
        timestamptz created_at
    }
```

Quan hệ chính:

- 1 user đặt nhiều orders, thêm nhiều wishlist, ghi nhiều history.
- 1 order có nhiều order_items và nhiều order_status_history.
- 1 category / 1 brand chứa nhiều products.
- 1 product xuất hiện trong nhiều order_items (qua snapshot) và nhiều wishlists.

## 3. Cấu hình & kết nối

### 3.1 Biến môi trường

| Key | Required | Default | Mô tả |
|---|---|---|---|
| `POSTGRES_DB` | Có | `cosme_shop` | Tên database |
| `POSTGRES_USER` | Có | `admin` | User DB |
| `POSTGRES_PASSWORD` | Có | `secret` | Password DB |
| `DATABASE_URL` | Có | -- | Full connection string asyncpg |

Connection string format:

```text
postgresql+asyncpg://<user>:<password>@<host>:<port>/<db>
```

Ví dụ trong `backend/.env`:

```dotenv
DATABASE_URL=postgresql+asyncpg://admin:secret@postgres:5432/cosme_shop
```

### 3.2 Connection pool

Cấu hình trong [backend/app/db/session.py](../../backend/app/db/session.py):

- `pool_size = 20` (số connection giữ sẵn).
- `max_overflow = 10` (connection dự phòng khi vượt pool).
- `echo = False` (đặt `True` để log SQL khi debug).

### 3.3 Debug DB local

- Mở Adminer: `http://localhost:8080`, nhập `postgres / 5432`, user `admin`, pass `secret`.
- Dùng `psql` qua Docker:

```bash
docker compose exec postgres psql -U admin -d cosme_shop
```

## 4. Chi tiết 9 bảng

### 4.1 `users`

Mục đích: lưu tài khoản đăng nhập + profile (User và Admin).

| Cột | Kiểu SQL | Null | Default | Ràng buộc | Ghi chú |
|---|---|---|---|---|---|
| `id` | `SERIAL` | No | auto | PK | |
| `email` | `VARCHAR(255)` | No | -- | UNIQUE, INDEX | Dùng để đăng nhập |
| `password_hash` | `VARCHAR(255)` | No | -- | | Bcrypt cost 12 |
| `full_name` | `VARCHAR(255)` | No | -- | | |
| `phone` | `VARCHAR(20)` | Yes | NULL | | Format VN (regex) |
| `address` | `TEXT` | Yes | NULL | | |
| `avatar_url` | `VARCHAR(500)` | Yes | NULL | | |
| `role` | `VARCHAR(20)` | No | `'user'` | CHECK (`'user'` \| `'admin'`) | |
| `is_active` | `BOOLEAN` | No | `true` | | Soft delete / khóa tài khoản |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | | |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` ON UPDATE | | |

Quan hệ ngược:

- 1 user → nhiều `orders`, `wishlists`, `order_status_history` (qua `created_by`).
- Không có FK trỏ tới user — user xóa mềm bằng `is_active=false`, không `DELETE`.

Lưu ý bảo mật: KHÔNG trả `password_hash` trong response schema, KHÔNG log token.

### 4.2 `categories`

Mục đích: danh mục sản phẩm (VD: Skincare, Makeup, Sunscreen).

| Cột | Kiểu SQL | Null | Default | Ràng buộc | Ghi chú |
|---|---|---|---|---|---|
| `id` | `SERIAL` | No | auto | PK | |
| `name` | `VARCHAR(255)` | No | -- | | |
| `slug` | `VARCHAR(255)` | No | -- | UNIQUE | VD: `skincare` |
| `description` | `TEXT` | Yes | NULL | | |
| `image_url` | `VARCHAR(500)` | Yes | NULL | | |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | | |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` ON UPDATE | | |

Quan hệ ngược: 1 category → nhiều `products`. Khi xóa category, nên soft delete (không xóa cứng) để tránh mất FK.

### 4.3 `brands`

Mục đích: thương hiệu sản phẩm (VD: The Ordinary, La Roche-Posay).

| Cột | Kiểu SQL | Null | Default | Ràng buộc | Ghi chú |
|---|---|---|---|---|---|
| `id` | `SERIAL` | No | auto | PK | |
| `name` | `VARCHAR(255)` | No | -- | | |
| `slug` | `VARCHAR(255)` | No | -- | UNIQUE | |
| `logo_url` | `VARCHAR(500)` | Yes | NULL | | |
| `description` | `TEXT` | Yes | NULL | | |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | | |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` ON UPDATE | | |

Quan hệ ngược: 1 brand → nhiều `products`.

### 4.4 `products`

Mục đích: sản phẩm — bảng phức tạp nhất, có nhiều JSON column phục vụ filter Routine Builder.

| Cột | Kiểu SQL | Null | Default | Ràng buộc | Ghi chú |
|---|---|---|---|---|---|
| `id` | `SERIAL` | No | auto | PK | |
| `name` | `VARCHAR(255)` | No | -- | | |
| `slug` | `VARCHAR(255)` | No | -- | UNIQUE | Auto-generate từ name |
| `description` | `TEXT` | Yes | NULL | | |
| `price` | `NUMERIC(12,0)` | No | -- | CHECK `> 0` | VNĐ |
| `sale_price` | `NUMERIC(12,0)` | Yes | NULL | CHECK `>= 0` | Giá khuyến mãi (optional) |
| `stock` | `INTEGER` | No | `0` | CHECK `>= 0` | |
| `category_id` | `INTEGER` | No | -- | FK → `categories.id` | |
| `brand_id` | `INTEGER` | No | -- | FK → `brands.id` | |
| `skin_types` | `JSONB` | Yes | NULL | | `string[]` |
| `concerns` | `JSONB` | Yes | NULL | | `string[]` |
| `key_ingredients` | `JSONB` | Yes | NULL | | `string[]` |
| `free_from` | `JSONB` | Yes | NULL | | `string[]` |
| `variants` | `JSONB` | Yes | NULL | | `Variant[]` — xem §5.5 |
| `sold_count` | `INTEGER` | No | `0` | | Best-seller ranking |
| `rating_avg` | `NUMERIC(3,2)` | No | `0` | | Đánh giá trung bình |
| `rating_count` | `INTEGER` | No | `0` | | Số lượt đánh giá |
| `is_active` | `BOOLEAN` | No | `true` | | Soft delete |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | | |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` ON UPDATE | | |

**Lưu ý:** bảng `products` **không** có cột `image_url` hay JSONB `images`.
Ảnh sản phẩm nằm ở bảng riêng `product_images` (§4.4b).

Quan hệ ngược: 1 product → nhiều `order_items` (qua snapshot), `wishlists`, `product_images`.

Lưu ý: Khi order, KHÔNG tham chiếu động từ `products` — phải snapshot `name`, `price`, `image`, `variant_info` vào `order_items`.

### 4.4b `product_images`

Mục đích: lưu ảnh sản phẩm trên Cloudinary. Mỗi sản phẩm có nhiều ảnh, 1 ảnh được đánh dấu là ảnh chính.

| Cột | Kiểu SQL | Null | Default | Ràng buộc | Ghi chú |
|---|---|---|---|---|---|
| `id` | `SERIAL` | No | auto | PK | |
| `product_id` | `INTEGER` | No | -- | FK → `products.id` ON DELETE CASCADE | |
| `public_id` | `VARCHAR(255)` | No | -- | UNIQUE | Khoá quản lý asset trên Cloudinary |
| `secure_url` | `VARCHAR(500)` | No | -- | | URL https canonical |
| `alt_text` | `VARCHAR(255)` | Yes | NULL | | Mô tả ảnh (SEO) |
| `width` | `INTEGER` | Yes | NULL | | Metadata từ Cloudinary |
| `height` | `INTEGER` | Yes | NULL | | Metadata từ Cloudinary |
| `format` | `VARCHAR(20)` | Yes | NULL | | `jpg` \| `png` \| `webp` |
| `position` | `INTEGER` | No | `0` | | Thứ tự hiển thị trong gallery |
| `is_main` | `BOOLEAN` | No | `false` | | Ảnh chính |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | | |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` ON UPDATE | | |

**Index**

| Index | Định nghĩa | Mục đích |
|---|---|---|
| `product_images_pkey` | PK (`id`) | — |
| `product_images_public_id_key` | UNIQUE (`public_id`) | Không trùng asset |
| `uq_product_images_one_main` | UNIQUE (`product_id`) WHERE `is_main` | Enforce **chỉ 1 ảnh chính** trong DB, chặn race condition khi 2 request upload song song |
| `ix_product_images_product_id` | (`product_id`) | Truy vấn ảnh theo sản phẩm |
| `ix_product_images_product_position` | (`product_id`, `position`) | Gallery `ORDER BY position` |

**Ghi chú**

- Không có cột `version`: upload dùng `overwrite=False` + `unique_filename=True` → mỗi lần upload là
  asset mới với `public_id` riêng, không có vấn đề cache stale.
- Không có cột `url` (http): URL chỉ tồn tại dạng `secure_url`. Các biến thể kích cỡ khác được
  sinh từ `public_id` lúc render (xem §6.5 của [01-system-design.md](01-system-design.md)).
- Ảnh đã bán **không** được xoá asset trên Cloudinary (chỉ gỡ row khỏi gallery) để lịch sử
  đơn hàng không bị 404.
- `position` được đánh lại liên tục `0..N-1` mỗi khi đổi ảnh chính: ảnh chính luôn ở `position = 0`,
  các ảnh còn lại là `1..N`. Service dùng chung helper `_promote_to_main()` cho cả
  `set_main_image`, `PATCH is_main=true` và upload ảnh mới với `is_main=true` để giữ invariant này.
  Endpoint `reorder` là ngoại lệ — admin được sắp xếp thủ công theo thứ tự tuỳ ý.

### 4.5 `orders`

Mục đích: đơn hàng của user.

| Cột | Kiểu SQL | Null | Default | Ràng buộc | Ghi chú |
|---|---|---|---|---|---|
| `id` | `SERIAL` | No | auto | PK | |
| `user_id` | `INTEGER` | No | -- | FK → `users.id` | |
| `order_code` | `VARCHAR(32)` | No | -- | UNIQUE | Format `ORD` + `YYYYMMDD` + 4 số random |
| `status` | `VARCHAR(20)` | No | `'pending'` | | State machine — xem §6 |
| `subtotal` | `NUMERIC(12,0)` | No | `0` | | Tổng tiền hàng |
| `shipping_fee` | `NUMERIC(12,0)` | No | `30000` | | |
| `discount` | `NUMERIC(12,0)` | No | `0` | | |
| `total` | `NUMERIC(12,0)` | No | `0` | | `subtotal + shipping_fee - discount` |
| `payment_method` | `VARCHAR(10)` | No | -- | CHECK (`'cod'` \| `'sepay'`) | |
| `payment_status` | `VARCHAR(10)` | No | `'unpaid'` | | `unpaid` \| `paid` |
| `paid_at` | `TIMESTAMPTZ` | Yes | NULL | | Set khi SePay webhook |
| `transaction_id` | `VARCHAR(64)` | Yes | NULL | | Từ SePay |
| `shipping_name` | `VARCHAR(255)` | No | -- | | |
| `shipping_phone` | `VARCHAR(20)` | No | -- | | Format VN |
| `shipping_address` | `TEXT` | No | -- | | |
| `tracking_code` | `VARCHAR(64)` | Yes | NULL | | Sinh giả khi `status=shipping` |
| `carrier` | `VARCHAR(64)` | Yes | NULL | | Tên hãng vận chuyển |
| `note` | `TEXT` | Yes | NULL | | |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | | |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` ON UPDATE | | |

Quan hệ ngược: 1 order → nhiều `order_items`, `order_status_history`.

### 4.6 `order_items`

Mục đích: dòng chi tiết của đơn hàng. Lưu snapshot tại thời điểm mua.

| Cột | Kiểu SQL | Null | Default | Ràng buộc | Ghi chú |
|---|---|---|---|---|---|
| `id` | `SERIAL` | No | auto | PK | |
| `order_id` | `INTEGER` | No | -- | FK → `orders.id` ON DELETE CASCADE | |
| `product_id` | `INTEGER` | No | -- | FK → `products.id` | |
| `product_name` | `VARCHAR(255)` | No | -- | | Snapshot |
| `product_price` | `NUMERIC(12,0)` | No | -- | | Snapshot |
| `product_image` | `VARCHAR(500)` | Yes | NULL | | Snapshot |
| `variant_info` | `JSONB` | Yes | NULL | | Snapshot — xem §5.6 |
| `qty` | `INTEGER` | No | `1` | CHECK `> 0` | |
| `subtotal` | `NUMERIC(12,0)` | No | `0` | | `product_price * qty` |

Lưu ý: Khi user cancel đơn (status còn `pending`/`confirmed`), cần hoàn stock cho `products` dựa trên `qty` và `variant_info` ở bảng này.

### 4.7 `order_status_history`

Mục đích: timeline trạng thái đơn hàng (pending → confirmed → packing → shipping → delivered).

| Cột | Kiểu SQL | Null | Default | Ràng buộc | Ghi chú |
|---|---|---|---|---|---|
| `id` | `SERIAL` | No | auto | PK | |
| `order_id` | `INTEGER` | No | -- | FK → `orders.id` ON DELETE CASCADE | |
| `status` | `VARCHAR(20)` | No | -- | | |
| `note` | `TEXT` | Yes | NULL | | VD: "Đã lấy hàng tại kho HN" |
| `created_by` | `INTEGER` | Yes | NULL | FK → `users.id` | User hoặc Admin tạo bản ghi |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | | |

Mỗi lần order chuyển trạng thái → insert 1 dòng. FE hiển thị theo thứ tự thời gian ngược.

### 4.8 `wishlists`

Mục đích: sản phẩm user yêu thích.

| Cột | Kiểu SQL | Null | Default | Ràng buộc | Ghi chú |
|---|---|---|---|---|---|
| `id` | `SERIAL` | No | auto | PK | |
| `user_id` | `INTEGER` | No | -- | FK → `users.id` ON DELETE CASCADE | |
| `product_id` | `INTEGER` | No | -- | FK → `products.id` ON DELETE CASCADE | |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | | |

UNIQUE composite: `UNIQUE(user_id, product_id)` — một user không thể thêm cùng 1 product 2 lần.

### 4.9 `payment_webhook_logs`

Mục đích: audit log webhook thanh toán — chống xử lý trùng (idempotent) và truy vết giao dịch.

| Cột | Kiểu SQL | Null | Default | Ràng buộc | Ghi chú |
|---|---|---|---|---|---|
| `id` | `SERIAL` | No | auto | PK | |
| `provider` | `VARCHAR(20)` | No | -- | | `sepay` |
| `transaction_id` | `VARCHAR(64)` | No | -- | UNIQUE `(provider, transaction_id)` | ID giao dịch từ cổng thanh toán |
| `order_code` | `VARCHAR(32)` | Yes | NULL | | Mã đơn map được; NULL nếu không khớp |
| `amount` | `INTEGER` | Yes | NULL | | Số tiền nhận (VNĐ) |
| `payload` | `JSONB` | Yes | NULL | | Raw payload webhook để đối chiếu |
| `status` | `VARCHAR(30)` | No | -- | | `received` \| `processed` \| `ignored` \| `unmatched` \| `cancelled` \| `amount_mismatch` |
| `error` | `TEXT` | Yes | NULL | | Mô tả lỗi xử lý |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | | |

Quan hệ ngược: không có FK (log tồn tại độc lập với đơn để giữ được lịch sử giao dịch lỗi).

Migration: `backend/alembic/versions/20261031_0900_c1d2e3f4a5b6_add_payment_webhook_logs.py`.

### 4.10 Partial unique index cho `orders.transaction_id`

Migration cùng file trên tạo partial unique index:

```sql
CREATE UNIQUE INDEX uq_orders_transaction_id
ON orders (transaction_id) WHERE transaction_id IS NOT NULL;
```

Ý nghĩa: 1 giao dịch thanh toán chỉ được gán cho tối đa 1 đơn — chống double-mark-paid khi webhook đến lại hoặc đối soát chạy song song.

## 5. Cấu trúc JSON columns

### 5.1 `products.skin_types`

```json
["oily", "combination"]
```

Enum giá trị: `oily | dry | combination | sensitive | normal`.

### 5.2 `products.concerns`

```json
["acne", "dark_spots"]
```

Enum gợi ý: `acne | dark_spots | wrinkles | dullness | dehydration | redness | pores | aging`.

### 5.3 `products.key_ingredients`

```json
["vitamin_c", "niacinamide", "hyaluronic_acid"]
```

### 5.4 `products.free_from`

```json
["alcohol", "fragrance", "parabens"]
```

Dùng để filter dị ứng trong Routine Builder: nếu user khai `allergies: ["alcohol"]`, loại sản phẩm có `"alcohol"` trong `free_from`.

### 5.5 `products.variants`

```json
[
  {
    "id": "v1",
    "name": "Do Ruby",
    "price": 350000,
    "stock": 20,
    "image_url": "https://.../do-ruby.jpg"
  },
  {
    "id": "v2",
    "name": "Hong Dao",
    "price": 350000,
    "stock": 15,
    "image_url": "https://.../hong-dao.jpg"
  }
]
```

Quy tắc:

- `variants = null` — sản phẩm không có biến thể, dùng `price`/`stock` chính.
- `variants = [...]` — mỗi variant có giá/stock riêng. Khi order/checkout phải chọn 1 variant cụ thể.
- Khi order, snapshot `variant_info = {"id": "v1", "name": "Do Ruby"}` vào `order_items` (xem §5.6).

### 5.6 `order_items.variant_info`

```json
{
  "id": "v1",
  "name": "Do Ruby"
}
```

`null` nếu sản phẩm không có variant. Chỉ lưu 2 field `id` + `name` để hiển thị — giá/stock đã snapshot ở `product_price`.

## 6. Quy tắc & ràng buộc

Trích từ [rules.md §7](rules.md):

- Mọi bảng có `id` (`SERIAL PK`) + `created_at` (`TIMESTAMPTZ`).
- Bảng có quan hệ thì có thêm `updated_at` (`TIMESTAMPTZ` với `ON UPDATE now()`).
- Mọi cột thời gian dùng `TIMESTAMPTZ` (KHÔNG `TIMESTAMP` — thiếu timezone).
- FK `ON DELETE CASCADE` cho `order_items`, `order_status_history`, `wishlists`. FK khác giữ `RESTRICT` ngầm định.
- Tên bảng: snake_case số nhiều (`products`, `order_items`).
- Tên cột: snake_case số ít (`name`, `price`, `created_at`).
- Soft delete: `is_active = false` thay vì `DELETE`. FK vẫn giữ nguyên.
- Migration bằng Alembic. KHÔNG sửa DB thủ công (kể cả dev).
- Snapshot fields (`order_items.product_name/price/variant_info`) lưu giá trị tại thời điểm mua, KHÔNG tham chiếu động về `products`.

### 6.1 Unique constraints tổng hợp

| Bảng | Cột / Composite |
|---|---|
| `users` | `email` |
| `categories` | `slug` |
| `brands` | `slug` |
| `products` | `slug` |
| `orders` | `order_code` |
| `orders` | `transaction_id` (partial unique, WHERE NOT NULL) |
| `payment_webhook_logs` | `(provider, transaction_id)` |
| `wishlists` | `(user_id, product_id)` |

## 7. Indexes đề xuất

Ngoài PK + UNIQUE đã tự tạo index, bổ sung index cho filter / join thường gặp:

| Bảng | Cột | Lý do |
|---|---|---|
| `products` | `is_active` | Filter public API (chỉ lấy active) |
| `products` | `category_id` | Filter theo category, join |
| `products` | `brand_id` | Filter theo brand, join |
| `products` | `name` | Search LIKE (cân nhắc khi dữ liệu lớn — có thể dùng GIN/trigram) |
| `orders` | `user_id` | User xem đơn của mình |
| `orders` | `status` | Admin filter đơn theo trạng thái |
| `orders` | `created_at` | Sort `newest`, phân trang |
| `order_items` | `product_id` | Best-seller ranking (SUM theo product_id) |

GIN index trên JSONB (cân nhắc khi cần query theo `skin_types`/`concerns`):

- `CREATE INDEX idx_products_skin_types ON products USING GIN (skin_types);`
- `CREATE INDEX idx_products_concerns ON products USING GIN (concerns);`

## 8. Migration với Alembic

### 8.1 Folder layout

```text
backend/
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── alembic.ini
└── app/
    └── db/
        ├── base.py    # Singleton Base
        └── session.py # engine + AsyncSessionLocal
```

### 8.2 Lệnh thường dùng

```bash
# Tạo migration mới (autogenerate từ model)
docker compose exec backend alembic revision --autogenerate -m "add wishlist"

# Apply migration
docker compose exec backend alembic upgrade head

# Rollback 1 bước
docker compose exec backend alembic downgrade -1

# Xem lịch sử
docker compose exec backend alembic history
```

### 8.3 Lưu ý quan trọng

- Phải fix "Singleton Base" ở [backend/app/db/base.py](../../backend/app/db/base.py) + [backend/app/db/session.py](../../backend/app/db/session.py) trước khi `--autogenerate` chạy đúng (xem §10).
- Sau khi đổi model, LUÔN chạy `--autogenerate` rồi review file migration — không commit file migration trống.

## 9. Code organization (Backend)

Theo [rules.md §4.3](rules.md), phải enforce **Singleton Base**:

```startLine:1:backend/app/db/base.py
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    __abstract__ = True

class IdMixin:
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
```

Mixin có sẵn:

- `IdMixin` — `id SERIAL PK`.
- `CreatedAtMixin` — `created_at TIMESTAMPTZ DEFAULT now()`.
- `UpdatedAtMixin` — `updated_at TIMESTAMPTZ DEFAULT now() ON UPDATE now()`.
- `TimestampMixin` = `CreatedAtMixin + UpdatedAtMixin`.

`backend/app/db/session.py` PHẢI `from app.db.base import Base` rồi mới tạo engine — KHÔNG khai báo `Base` mới.

Mọi model ở `backend/app/model/` (số ít) kế thừa cùng `Base` để Alembic `--autogenerate` thấy đủ schema.

Ví dụ:

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin

class User(Base, TimestampMixin):
    __tablename__ = 'user'

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # ...
```

## 10. Vấn đề hiện tại cần xử lý

Trích từ [rules.md Phụ lục](rules.md) + quan sát code:

1. **Sai model `User`** ở [backend/app/model/user.py](../../backend/app/model/user.py) — đang dùng `username` + `password` (plain). Cần đổi sang:
   - `email VARCHAR(255) UNIQUE` (login).
   - `password_hash VARCHAR(255)` (bcrypt cost 12).
   - Bổ sung `full_name`, `phone`, `address`, `avatar_url`, `role`, `is_active` theo §4.1.
2. **Hai `Base` chồng lấn** ở [backend/app/db/session.py](../../backend/app/db/session.py) — đang `from sqlalchemy.orm import declarative_base` và tạo `Base = declarative_base()` mới trong khi [backend/app/db/base.py](../../backend/app/db/base.py) đã có `Base` riêng. Hệ quả: Alembic chỉ thấy model nào được khai báo trên cùng `Base` của nó. Phải enforce Singleton Base.
3. **7 model còn lại chưa tồn tại** — cần scaffold `category.py`, `brand.py`, `product.py`, `order.py`, `order_item.py`, `order_status_history.py`, `wishlist.py` theo schema §4.
4. **Folder `alembic/` chưa init** — cần `alembic init backend/alembic` và trỏ `target_metadata = Base.metadata` trong `env.py`.

## 11. Seed data

Lệnh seed (xem [03-tech-stack.md §5.3](03-tech-stack.md)):

```bash
docker compose exec backend python -m app.scripts.seed
```

Seed tối thiểu đề xuất:

- **1 admin user** — `role='admin'`, `is_active=true`.
- **1 user mẫu** — để test login + checkout.
- **5-10 categories** — Skincare, Makeup, Sunscreen, Cleanser, Toner, Serum, Mask, Lip Care, Eye Care, Body Care.
- **5 brands phổ biến** — The Ordinary, La Roche-Posay, Cocoon, Innisfree, Klairs.
- **20-30 products**, bao gồm:
  - Vài sản phẩm KHÔNG có variant (dùng `price`/`stock` chính).
  - Vài sản phẩm CÓ variants (son môi nhiều màu).
  - Đầy đủ JSON fields (`skin_types`, `concerns`, `key_ingredients`, `free_from`) để test Routine Builder.

Mục đích seed: có data để demo từ máy sạch mà không cần nhập tay.

## 12. Tham chiếu chéo

- Sơ đồ ERD gốc: [01-system-design.md §3.1](01-system-design.md).
- Quy tắc DB tổng: [rules.md §7](rules.md).
- Biến môi trường: [03-tech-stack.md §4.1](03-tech-stack.md).
- Nghiệp vụ order + payment: [02-business-requirement.md §3.4-3.6](02-business-requirement.md).
- State machine đơn hàng: [02-business-requirement.md §5](02-business-requirement.md).
- Routine Builder (filter JSON): [02-business-requirement.md §3.7](02-business-requirement.md).
