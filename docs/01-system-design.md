# Thiết kế hệ thống — Web Mỹ phẩm

Tài liệu này mô tả kiến trúc tổng thể, các thành phần, sơ đồ quan hệ cơ sở dữ liệu, các luồng nghiệp vụ chính và các quyết định thiết kế quan trọng của hệ thống bán mỹ phẩm `cosme-shop`.

## 1. Tổng quan kiến trúc

Hệ thống theo mô hình monorepo 3 module, triển khai dạng client-server với backend làm API gateway trung tâm.

```mermaid
flowchart LR
    User[Khach hang]
    FE[Frontend React SPA]

    subgraph Backend["Backend FastAPI port 8000"]
        Auth[Auth]
        Product[Product]
        CartProxy[Cart read only]
        Order[Order]
        Payment[Payment]
        Admin[Admin]
    end

    AI[AIService FastAPI port 8001]
    DB[(PostgreSQL 17<br/>Schema public)]

    subgraph SePay["SePay Gateway"]
        QR[QR / Webhook]
    end

    User --> FE
    FE -->|"REST + JWT"| Backend
    Backend -->|"SQLAlchemy async"| DB
    Backend -->|"httpx internal"| AI
    User -->|"Chuyen khoan"| SePay
    SePay -->|"Webhook HTTPS"| Backend
```

Ba module chính:

- `/backend` (FastAPI, port `8000`) — API gateway, xử lý nghiệp vụ, kết nối database, gọi AI service, nhận webhook SePay.
- `/ai` (FastAPI, port `8001`) — Service AI riêng, gọi Gemini API để tạo Routine Builder.
- `/fe` (React + Vite + TypeScript) — Single-page app cho khách hàng và admin.

## 2. Thành phần hệ thống

### 2.1 Frontend (React SPA)

- Vai trò: giao diện người dùng và admin.
- Giao tiếp: REST API với backend qua Axios.
- State: Zustand (client state) + TanStack Query (server state).
- Deploy: static files, có thể serve qua Nginx hoặc Vite preview.

### 2.2 Backend (FastAPI)

- Vai trò: API gateway, xử lý toàn bộ nghiệp vụ.
- Giao tiếp:
  - Nhận request từ FE.
  - Gọi AI service qua HTTP nội bộ.
  - Nhận webhook từ SePay.
  - Truy vấn PostgreSQL async.
- Auth: JWT HS256, token hết hạn sau 1 ngày.

### 2.3 AI Service (FastAPI riêng)

- Vai trò: xử lý logic AI, tách khỏi backend để dễ bảo trì.
- Giao tiếp:
  - Nhận request từ backend (không expose public).
  - Gọi Gemini API (`google-genai` SDK).
- Không có: database, auth, session.
- Endpoint duy nhất: `POST /routine` (tạo skincare routine từ quiz input).

### 2.4 Database (PostgreSQL 17)

- Một database duy nhất: `cosme_shop`.
- 9 bảng nghiệp vụ trong schema `public` (chi tiết ở mục 3).
- Không dùng `pgvector` — AI dùng Gemini API trực tiếp, không có embedding.

### 2.5 SePay Gateway

- Vai trò: xác nhận chuyển khoản qua webhook.
- Cơ chế xác thực: HMAC-SHA256 trên raw body (`X-SePay-Signature` + `X-SePay-Timestamp`), fallback API key.
- Flow:

```mermaid
sequenceDiagram
    participant U as User
    participant FE
    participant BE as Backend
    participant DB
    participant SP as SePay
    participant Bank as Ngan hang

    U->>FE: Chon SePay, checkout
    FE->>BE: POST /api/orders (payment_method=sepay)
    BE->>DB: Tao order, payment_status=unpaid
    BE-->>FE: order_code + QR VietQR
    U->>Bank: Chuyen khoan noi dung ORDxxxx
    Bank->>SP: Giao dich moi
    SP->>BE: POST /api/payment/sepay-webhook
    BE->>BE: Verify HMAC-SHA256 raw body + timestamp skew
    BE->>DB: INSERT payment_webhook_logs (idempotent theo tx_id)
    BE->>DB: Update payment_status=paid
    BE-->>SP: {"success": true}
    FE-->>U: Hien thi "Da thanh toan" (polling 4s)
```

## 3. Thiết kế database

### 3.1 Sơ đồ quan hệ

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
    products ||--o{ product_images : "co anh"

    users {
        int id PK
        string email UK
        string password_hash
        string full_name
        string phone
        text address
        string avatar_url
        string role
        bool is_active
        timestamptz created_at
        timestamptz updated_at
    }

    categories {
        int id PK
        string name
        string slug UK
        text description
        string image_url
    }

    brands {
        int id PK
        string name
        string slug UK
        string logo_url
        text description
    }

    products {
        int id PK
        string name
        string slug UK
        text description
        numeric price
        numeric sale_price
        int stock
        int category_id FK
        int brand_id FK
        json skin_types
        json concerns
        json key_ingredients
        json free_from
        json variants
        int sold_count
        numeric rating_avg
        int rating_count
        bool is_active
        timestamptz created_at
        timestamptz updated_at
    }

    product_images {
        int id PK
        int product_id FK
        string public_id UK
        string secure_url
        string alt_text
        int width
        int height
        string format
        int position
        bool is_main
        timestamptz created_at
        timestamptz updated_at
    }

    orders {
        int id PK
        int user_id FK
        string order_code UK
        string status
        numeric subtotal
        numeric shipping_fee
        numeric discount
        numeric total
        string payment_method
        string payment_status
        timestamptz paid_at
        string transaction_id
        string shipping_name
        string shipping_phone
        text shipping_address
        string tracking_code
        string carrier
        text note
        timestamptz created_at
        timestamptz updated_at
    }

    order_items {
        int id PK
        int order_id FK
        int product_id FK
        string product_name
        numeric product_price
        string product_image
        json variant_info
        int qty
        numeric subtotal
    }

    order_status_history {
        int id PK
        int order_id FK
        string status
        text note
        int created_by FK
        timestamptz created_at
    }

    wishlists {
        int id PK
        int user_id FK
        int product_id FK
        timestamptz created_at
    }

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

### 3.2 Cấu trúc JSON variants

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

**Quy tắc:**

- `variants = null` — sản phẩm không có biến thể, dùng `price`/`stock` chính.
- `variants = [...]` — mỗi variant có giá/stock riêng.
- Khi order, snapshot `variant_info = {"id": "v1", "name": "Do Ruby"}` vào `order_items`.

## 4. Thiết kế API

### 4.1 Quy ước chung

- Prefix: `/api`.
- Response thành công: `{ "data": ..., "message": "OK" }`.
- Response lỗi: `{ "detail": "...", "code": "ERROR_CODE" }`.
- Auth: `Authorization: Bearer <JWT>`.
- Pagination: `?page=1&size=20` → `{ data, total, page, size }`.
- Thời gian: ISO 8601 UTC.

### 4.2 Danh sách endpoints

| Nhóm | Method | Path | Phân quyền |
|---|---|---|---|
| Auth | POST | `/api/auth/register` | Public |
| Auth | POST | `/api/auth/login` | Public |
| Auth | GET | `/api/auth/me` | User |
| Auth | PATCH | `/api/auth/me` | User |
| Auth | POST | `/api/auth/change-password` | User |
| Products | GET | `/api/products` | Public (filter + paginate) |
| Products | GET | `/api/products/{id}` | Public |
| Products | GET | `/api/products/{id}/similar` | Public |
| Products | GET | `/api/products/best-sellers` | Public |
| Products | POST | `/api/products` | Admin |
| Products | PATCH | `/api/products/{id}` | Admin |
| Products | DELETE | `/api/products/{id}` | Admin |
| Categories | GET | `/api/categories` | Public |
| Categories | POST | `/api/categories` | Admin |
| Categories | PATCH | `/api/categories/{id}` | Admin |
| Categories | DELETE | `/api/categories/{id}` | Admin |
| Brands | GET | `/api/brands` | Public |
| Brands | POST | `/api/brands` | Admin |
| Brands | PATCH | `/api/brands/{id}` | Admin |
| Brands | DELETE | `/api/brands/{id}` | Admin |
| Orders | POST | `/api/orders` | User (checkout) |
| Orders | GET | `/api/orders` | User (đơn của mình) |
| Orders | GET | `/api/orders/{id}` | User (chi tiết + history) |
| Orders | POST | `/api/orders/{id}/cancel` | User |
| Orders | GET | `/api/admin/orders` | Admin |
| Orders | PATCH | `/api/admin/orders/{id}/status` | Admin |
| Users | GET | `/api/admin/users` | Admin (phân trang server-side) |
| Users | PATCH | `/api/admin/users/{id}/toggle-active` | Admin |
| Dashboard | GET | `/api/admin/stats` | Admin (thống kê tổng quan) |
| Payment | POST | `/api/payment/sepay-webhook` | SePay (HMAC-SHA256) |
| Payment | GET | `/api/payment/status/{order_id}` | User (chủ đơn) hoặc Admin |
| Payment | POST | `/api/payment/reconcile` | Admin (đối soát SePay API v2) |
| Wishlist | GET | `/api/wishlist` | User |
| Wishlist | POST | `/api/wishlist/{product_id}` | User |
| Wishlist | DELETE | `/api/wishlist/{product_id}` | User |
| Upload | POST | `/api/upload/product-image/{product_id}` | Admin |
| Upload | GET | `/api/upload/product-image/product/{product_id}` | Admin |
| Upload | PATCH | `/api/upload/product-image/{image_id}` | Admin |
| Upload | PATCH | `/api/upload/product-image/{image_id}/set-main` | Admin |
| Upload | PATCH | `/api/upload/product-image/{product_id}/reorder` | Admin |
| Upload | DELETE | `/api/upload/product-image/{image_id}` | Admin |

### 4.3 AI Service endpoints (nội bộ)

- `POST /routine` — nhận quiz + danh sách sản phẩm đã match → gọi Gemini → trả routine.

## 5. Luồng nghiệp vụ chính

### 5.1 Đặt hàng COD

```mermaid
sequenceDiagram
    participant U as User
    participant FE
    participant BE as Backend
    participant DB

    U->>FE: Them gio hang (Zustand)
    U->>FE: Checkout chon COD
    FE->>BE: POST /api/orders
    BE->>DB: Tao order + order_items snapshot
    BE->>DB: Insert order_status_history (pending)
    BE-->>FE: order_code
    FE-->>U: Trang xac nhan
    Note over U,FE: Admin xu ly
    U->>BE: PATCH /api/admin/orders/{id}/status
    BE->>DB: Update status + insert history
    U->>FE: Xem timeline
```

### 5.2 Đặt hàng SePay

```mermaid
sequenceDiagram
    participant U as User
    participant FE
    participant BE as Backend
    participant DB
    participant SP as SePay
    participant Bank

    U->>FE: Checkout chon SePay
    FE->>BE: POST /api/orders
    BE->>DB: Tao order (payment_status=unpaid)
    BE-->>FE: QR code + ma CK
    U->>Bank: Chuyen khoan noi dung ORDxxxx
    Bank->>SP: Phat hien giao dich
    SP->>BE: POST /api/payment/sepay-webhook
    BE->>BE: Verify Apikey
    BE->>DB: payment_status=paid
    BE-->>SP: success
    FE-->>U: Hien thi Da thanh toan (polling)
```

### 5.3 Routine Builder

```mermaid
sequenceDiagram
    participant U as User
    participant FE
    participant BE as Backend
    participant DB
    participant AI as AIService
    participant G as Gemini

    U->>FE: Tra loi 5 cau quiz
    FE->>BE: POST /api/ai/routine
    BE->>DB: Query product match skin/concerns/price
    BE->>AI: POST /routine (products + quiz)
    AI->>G: Prompt "chon routine 4-5 buoc"
    G-->>AI: Response JSON
    AI-->>BE: {steps, note}
    BE-->>FE: Routine + product cards
    U->>FE: Them tat ca vao gio
```

## 6. Bảo mật

### 6.1 Auth

- JWT HS256, secret key lưu trong `.env`.
- Token hết hạn sau 1 ngày.
- Password hash bằng bcrypt (cost 12).
- Không lưu plaintext password, không log token.

### 6.2 Phân quyền

- Dependency `get_current_user` — bắt buộc đăng nhập.
- Dependency `get_current_admin` — check role == `"admin"`.
- Mọi endpoint admin đều có check `[admin]` trong service layer.

### 6.3 Webhook SePay

- Xác thực ưu tiên HMAC-SHA256 trên **raw body** (header `X-SePay-Signature: sha256=<hex>`, `X-SePay-Timestamp`).
- Chuỗi ký: `HMAC_SHA256(secret, f"{timestamp}.{raw_body}")`, so sánh constant-time (`hmac.compare_digest`).
- Chống replay: timestamp lệch quá 300 giây → 401.
- Fallback: `Authorization: Apikey <SEPAY_API_KEY>` nếu không bật HMAC.
- Idempotent: unique constraint `(provider, transaction_id)` trên bảng `payment_webhook_logs` → giao dịch trùng bị bỏ qua.
- Đơn đã `cancelled` → KHÔNG đánh dấu paid, ghi log `cancelled` để hoàn tiền thủ công.
- Thiếu tiền (`amount_in < total`) → ghi log `amount_mismatch`, giữ `unpaid`.
- `transaction_id` được bảo đảm unique trên `orders` (partial unique index) → 1 giao dịch không gán cho 2 đơn.
- Đối soát thủ công: `POST /api/payment/reconcile` quét SePay API v2 và đánh paid các đơn còn `unpaid`.

### 6.4 CORS

- `allow_origins` đọc từ biến môi trường `CORS_ORIGINS` (JSON array), mặc định `["http://localhost:3000"]`.
- `allow_credentials=True`

### 6.5 Upload ảnh

- Chỉ admin upload được (`Depends(get_current_admin)`).
- Giới hạn 5MB (`CLOUDINARY_MAX_FILE_SIZE`), chỉ chấp nhận jpg/png/webp.
  Danh sách format phải khớp với `ALLOWED_UPLOAD_FORMATS` trong `app/core/cloudinary.py` —
  nếu API cho phép format mà Cloudinary chặn thì user chỉ thấy lỗi 502 thay vì thông báo rõ ràng.
- Validate 2 lớp: content-type của client + magic bytes của file thực (chống file giả mạo).
- Lưu trên **Cloudinary** (signed upload qua backend, không expose API secret ra client).
- Mỗi sản phẩm có nhiều ảnh, lưu trong bảng `product_images` (xem [04-database.md §4.4b](04-database.md)).
- Upload là blocking I/O → chạy trong `run_in_threadpool` để không chặn event loop.

**Cấu trúc folder trên Cloudinary**

`CLOUDINARY_FOLDER` là folder gốc (mặc định `cosme-shop`). Mỗi sản phẩm nằm trong folder con
`{CLOUDINARY_FOLDER}/products/{product_id}`, do `build_product_folder()` trong
`app/core/cloudinary.py` sinh ra. `upload_image()` **bắt buộc** nhận `folder` tường minh —
không có default — để tránh hai nơi cùng định nghĩa folder và sinh path lặp
(ví dụ `cosme-shop/products/products/1`).

**Ảnh chính luôn ở đầu gallery**

`product_images.position` quyết định thứ tự hiển thị. Khi đổi ảnh chính
(`set_main_image`, `PATCH is_main=true`, hoặc upload ảnh mới với `is_main=true`),
service gọi chung một helper `_promote_to_main()` để đặt ảnh chính ở `position = 0`
và đánh lại `position` của các ảnh còn lại thành `1..N` liên tục. Việc bỏ cờ
`is_main` được thực hiện ở câu lệnh riêng trước khi đặt ảnh mới, tránh vi phạm
unique index `uq_product_images_one_main`. Xung đột do race condition được bắt
lại thành HTTP 409 thay vì 500.

Ngoại lệ: endpoint `reorder` cho admin sắp xếp thủ công theo thứ tự tuỳ ý
(bao gồm việc di chuyển ảnh chính), nên thứ tự sau reorder không bắt buộc có
ảnh chính ở đầu.

**Chiến lược ảnh: 1 ảnh gốc + Cloudinary transform lúc hiển thị**

Admin upload **một** file gốc duy nhất (khuyến nghị ≥ 1600×1600 px, vuông hoặc gần vuông).
Cloudinary tự resize/crop/convert (`q_auto`, `f_auto`) khi render:

| Nơi hiển thị | Kích thước | Transformation |
|---|---|---|
| Card sản phẩm | 600×600 | `w_600,h_600,c_fill` |
| Trang chi tiết | 1200×840 | `w_1200,h_840,c_limit` |
| Giỏ / wishlist | 160×160 | `w_160,h_160,c_fill` |
| Thumb bảng admin | 200×200 | `w_200,h_200,c_fill` |

Biến thể được sinh từ `public_id` lúc runtime (không lưu nhiều URL trong DB → không stale).
Backend trả kèm `image_urls: { card, detail, thumb }` cho mỗi sản phẩm.

**API endpoints**

| Method | Path | Mô tả |
|---|---|---|
| `POST` | `/api/upload/product-image/{product_id}` | Upload 1 ảnh (multipart: `file`, `alt_text`, `is_main`) |
| `GET` | `/api/upload/product-image/product/{product_id}` | Danh sách ảnh theo thứ tự `position` |
| `PATCH` | `/api/upload/product-image/{image_id}/set-main` | Đặt ảnh chính (unset các ảnh khác) |
| `PATCH` | `/api/upload/product-image/{image_id}` | Cập nhật metadata (`alt_text`, `position`, `is_main`) |
| `PATCH` | `/api/upload/product-image/{product_id}/reorder` | Đổi thứ tự: body `{"image_ids": [3,1,2]}` |
| `DELETE` | `/api/upload/product-image/{image_id}` | Xoá ảnh khỏi gallery |

**Quy tắc xoá an toàn lịch sử đơn hàng**

`order_items.product_image` lưu snapshot URL (không FK). Trước khi xoá asset trên Cloudinary,
kiểm tra ảnh đã được snapshot vào đơn hàng chưa:
- **Chưa bán** → xoá asset Cloudinary + xoá row DB.
- **Đã bán** → **giữ asset trên Cloudinary**, chỉ gỡ row khỏi gallery (lịch sử đơn hàng không bị 404).

## 7. Triển khai

### 7.1 Local dev (Docker Compose)

Cấu hình 5 services:

```mermaid
flowchart LR
    Dev[Developer]
    Dev -->|docker compose up| DC[Docker Compose]

    DC --> PG[(postgres:17-alpine<br/>5432)]
    DC --> AD[adminer<br/>8080]
    DC --> BE[backend<br/>8000]
    DC --> AI[ai<br/>8001]
    DC --> FE[fe<br/>3000]

    BE --> PG
    BE --> AI
```

| Service | Port | Image / Build |
|---|---|---|
| postgres | 5432 | `postgres:17-alpine` |
| adminer | 8080 | `adminer:latest` |
| backend | 8000 | build từ `./backend` |
| ai | 8001 | build từ `./ai` |
| fe | 3000 | build từ `./fe` |

### 7.2 Webhook SePay khi dev

Do SePay cần URL public HTTPS, có 3 cách:

- **Cách 1 — Cloudflare Tunnel (khuyên dùng):**

```bash
cloudflared tunnel --url http://localhost:8000
```

Nhận URL `https://xxx.trycloudflare.com` → cấu hình trên SePay.

- **Cách 2 — VPS làm relay:** VPS nhận webhook → forward về local qua SSH tunnel.
- **Cách 3 — ngrok:**

```bash
ngrok http 8000
```

### 7.3 Production (nếu deploy thật)

- VPS Ubuntu 22.04.
- Nginx reverse proxy + Let's Encrypt SSL.
- Docker Compose chạy 4 service (bỏ adminer).
- PostgreSQL backup định kỳ.

## 8. Hiệu năng & mở rộng

### 8.1 Hiệu năng hiện tại

- Async toàn bộ (FastAPI + SQLAlchemy async).
- Connection pool 20, max overflow 10.
- TanStack Query cache 5 phút trên FE.

### 8.2 Điểm nghẽn tiềm ẩn

- AI service gọi Gemini API — có thể chậm 2–5s.
- Webhook SePay — cần idempotent để tránh duplicate.

### 8.3 Mở rộng (không làm trong đồ án)

- Redis cache cho product list.
- Celery cho background job (email, PDF).
- CDN cho ảnh sản phẩm.
- Load balancer cho AI service.

## 9. Quyết định thiết kế quan trọng

| Quyết định | Lý do |
|---|---|
| Giỏ hàng ở FE | Guest cũng có giỏ, không cần API riêng |
| Snapshot giá vào `order_items` | Đơn cũ không đổi khi admin sửa giá |
| Variants dạng JSON | Không cần bảng riêng, đủ cho đồ án |
| AI service tách riêng | Dễ bảo trì, có thể thay LLM provider |
| Không dùng pgvector | AI dùng Gemini API trực tiếp, không embedding |
| COD + SePay | COD ổn định, SePay có điểm nhấn |
| Không refresh token | Overkill cho đồ án |
| PostgreSQL 17 | Phiên bản stable mới nhất, asyncpg hỗ trợ đầy đủ |
| Frontend TypeScript + React 18 | Type safety, tương thích chính thức với antd v5 |
