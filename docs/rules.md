# E-Commerce Project Rules — cosme-shop

Tài liệu này là bộ quy tắt bắt buộc khi triển khai dự án `cosme-shop`. Mọi code mới (do AI hoặc dev) phải tuân thủ. Khi cần thay đổi, phải cập nhật file này trước.

Các tài liệu liên quan:

- [01-system-design.md](01-system-design.md) — kiến trúc, database schema, flow nghiệp vụ.
- [02-business-requirement.md](02-business-requirement.md) — nghiệp vụ, vai trò, kịch bản demo.
- [03-tech-stack.md](03-tech-stack.md) — dependencies, ports, biến môi trường.

## 1. Tổng quan dự án

- Web thương mại điện tử bán mỹ phẩm, monorepo 3 module: `/backend`, `/ai`, `/fe`.
- Thời gian: 1 tháng.
- MVP: core e-commerce (auth, product, cart, order, payment, admin) + 1 tính năng AI (**Routine Builder Quiz**).
- Tên dự án: `cosme-shop`.

## 2. Stack — không thay đổi

### 2.1 Backend (`/backend`)

- FastAPI + Uvicorn (port `8000`).
- SQLAlchemy 2.x async + Alembic (migration).
- PostgreSQL 17 (driver `asyncpg`).
- Pydantic v2 + pydantic-settings.
- `python-jose[cryptography]` + `passlib[bcrypt]` + `bcrypt` (JWT HS256).
- `httpx` (gọi sang AI service).

### 2.2 AI service (`/ai`)

- FastAPI + Uvicorn (port `8001`).
- Gemini API qua `google-genai` SDK — **KHÔNG embedding, KHÔNG pgvector**.
- Có thể fallback Ollama local qua biến `LLM_PROVIDER`.
- **KHÔNG** auth, **KHÔNG** database nghiệp vụ, **KHÔNG** session.

### 2.3 Frontend (`/fe`)

- Vite + React 18 + **TypeScript** (KHÔNG dùng JavaScript).
- React Router v6.
- Zustand (client state: auth, cart, notification).
- TanStack Query v5 (server state).
- Axios (HTTP).
- Ant Design v5.
- **KHÔNG dùng:** Redux, Next.js, styled-components, Tailwind, MUI, React 18.

### 2.4 Database

- PostgreSQL 17.
- **KHÔNG** extension `pgvector` (đã loại bỏ).
- Một schema `public` duy nhất (đã loại bỏ schema `ai`).

### 2.5 Hạ tầng

- Docker Compose: 5 services (`postgres`, `adminer`, `backend`, `ai`, `fe`).
- Mọi service dev chạy trong Docker — KHÔNG cài runtime trực tiếp lên máy.

## 3. Cấu trúc thư mục

```text
cosme-shop/
├── docker-compose.yml
├── .env.example
├── README.md
├── docs/
│   ├── 01-system-design.md
│   ├── 02-business-requirement.md
│   ├── 03-tech-stack.md
│   └── rules.md
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── db/
│   │   │   ├── base.py            # Base + mixins (SINGLETON)
│   │   │   └── session.py         # engine + AsyncSessionLocal + get_db
│   │   ├── model/                 # SQLAlchemy model (số ít)
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── category.py
│   │   │   ├── brand.py
│   │   │   ├── product.py
│   │   │   ├── order.py
│   │   │   ├── order_item.py
│   │   │   ├── order_status_history.py
│   │   │   └── wishlist.py
│   │   ├── schemas/               # Pydantic schemas
│   │   ├── api/                   # routers (KHÔNG có cart.py — cart ở FE)
│   │   │   ├── deps.py
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── products.py
│   │   │   ├── categories.py
│   │   │   ├── brands.py
│   │   │   ├── orders.py
│   │   │   ├── payment.py         # SePay webhook
│   │   │   ├── wishlist.py
│   │   │   ├── admin.py           # admin orders + admin users
│   │   │   └── ai.py              # proxy sang AI service
│   │   └── service/               # business logic (số ít)
│   │       ├── auth_service.py
│   │       ├── user_service.py
│   │       ├── product_service.py
│   │       ├── order_service.py
│   │       ├── payment_service.py
│   │       ├── wishlist_service.py
│   │       └── ai_service.py
│   ├── alembic/
│   ├── alembic.ini
│   ├── requirements.txt
│   └── Dockerfile
├── ai/
│   ├── app/
│   │   ├── main.py
│   │   ├── routine.py
│   │   ├── gemini_client.py
│   │   └── schemas.py
│   ├── requirements.txt
│   └── Dockerfile
└── fe/
    ├── src/
    │   ├── api/                   # axios + endpoint files
    │   ├── components/
    │   ├── pages/
    │   │   ├── user/
    │   │   └── admin/
    │   ├── store/                 # zustand: auth, cart, notification
    │   ├── hooks/                 # custom hooks
    │   ├── utils/
    │   ├── types/                 # TS types
    │   ├── App.tsx
    │   └── main.tsx
    ├── package.json
    ├── tsconfig.json
    └── Dockerfile
```

## 4. Quy tắc Backend (FastAPI)

### 4.1 Cấu trúc code

- `api/` chỉ xử lý HTTP layer (validate input, gọi service, trả response).
- Business logic đặt trong `service/`. KHÔNG viết logic nghiệp vụ trong router.
- `model/` cho SQLAlchemy ORM, `schemas/` cho Pydantic — không trộn lẫn.
- File name: `snake_case`. Class name: `PascalCase`. Function/variable: `snake_case`.
- Một file không quá 200 dòng — tách nhỏ khi cần.

### 4.2 Async — bắt buộc

- Mọi endpoint dùng `async def`.
- Dùng `AsyncSession` của SQLAlchemy, không dùng session đồng bộ.
- Khi gọi AI service, dùng `httpx.AsyncClient` (không dùng `requests`).

### 4.3 Singleton Base — bắt buộc

- `db/base.py` định nghĩa duy nhất một `Base = DeclarativeBase()` + các mixin (`IdMixin`, `TimestampMixin`).
- `db/session.py` phải `from app.db.base import Base` rồi mới tạo engine — KHÔNG được khai báo `Base` mới.
- Mọi model phải kế thừa cùng `Base` này để Alembic `--autogenerate` thấy đủ schema.

### 4.4 Response format — bắt buộc

Mọi endpoint (thành công lẫn lỗi) phải trả theo format thống nhất:

```json
// Thành công
{ "data": { ... }, "message": "OK" }

// Lỗi
{ "detail": "Mô tả lỗi", "code": "ERROR_CODE" }
```

- HTTP status code chuẩn: `200`, `201`, `400`, `401`, `403`, `404`, `409`, `500`.
- Dùng `app.exception_handler` để enforce format — bắt cả `HTTPException`, `RequestValidationError`, và exception chưa lường trước.
- Pagination: `?page=1&size=20` → `{ "data": [...], "total": 100, "page": 1, "size": 20, "message": "OK" }`.

### 4.5 Auth

- JWT HS256 trong header `Authorization: Bearer <token>`.
- Dependency `get_current_user` (bắt buộc đăng nhập).
- Dependency `get_current_admin` (check `role == "admin"`).
- Password hash bằng bcrypt cost 12, lưu field `password_hash`. KHÔNG lưu plain text, không log token.
- Không trả `password_hash` trong response schema.

### 4.6 Validation

- Mọi input dùng Pydantic schema, không nhận `dict` raw.
- Response schema có `model_config = ConfigDict(from_attributes=True)`.
- Email dùng `EmailStr`, phone dùng regex VN, số dùng `Decimal` cho tiền tệ.

### 4.7 Ví dụ router chuẩn

```python
# app/api/products.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.product import ProductCreate, ProductResponse
from app.service import product_service
from app.api.deps import get_current_admin

router = APIRouter(prefix="/api/products", tags=["products"])

@router.get("", response_model=list[ProductResponse])
async def list_products(db: AsyncSession = Depends(get_db)):
    products = await product_service.get_all(db)
    return products

@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
    _admin = Depends(get_current_admin),
):
    return await product_service.create(db, payload)
```

## 5. Quy tắc AI Service

### 5.1 Phạm vi

- Chỉ có **một** endpoint chính: `POST /routine`.
- KHÔNG auth, KHÔNG truy vấn bảng nghiệp vụ.
- Input: `{ "products": [...], "quiz": {...} }` (danh sách sản phẩm đã được backend filter + quiz input).
- Output: `{ "steps": [...], "note": "..." }`.

### 5.2 Fallback & timeout

- Lỗi/timeout Gemini → trả message mặc định tiếng Việt: `"Xin lỗi, tôi đang bận. Vui lòng thử lại."`.
- Timeout tối đa `15` giây cho mỗi request Gemini.

### 5.3 Biến môi trường

- `GEMINI_API_KEY` — bắt buộc khi `LLM_PROVIDER=gemini`.
- `LLM_PROVIDER` = `gemini` (mặc định) hoặc `ollama` (nâng cấp sau).
- `OLLAMA_URL` — bắt buộc khi `LLM_PROVIDER=ollama`.

## 6. Quy tắc Frontend (React + TypeScript)

### 6.1 Nguyên tắc chung

- Component function, KHÔNG dùng class component.
- Mỗi file 1 component chính. Tên file PascalCase (`ProductCard.tsx`).
- Tên component PascalCase, tên hàm/biến camelCase.
- Dùng `const` mặc định, chỉ dùng `let` khi cần reassign. KHÔNG dùng `var`.
- TypeScript strict mode bật (`noUnusedLocals`, `noUnusedParameters`).
- Khai báo type trong `types/` hoặc inline — KHÔNG dùng `any`. Dùng `unknown` + type guard nếu cần.

### 6.2 State management — bắt buộc tuân thủ

**Server state → TanStack Query:**

- Danh sách sản phẩm, chi tiết sản phẩm, đơn hàng, thông tin user, danh mục, thương hiệu, wishlist.
- Dùng `useQuery` cho GET, `useMutation` cho POST/PUT/PATCH/DELETE.
- Sau mutation thành công → `queryClient.invalidateQueries({ queryKey: [...] })`.
- KHÔNG lưu server data vào Zustand.

**Client state → Zustand:**

- Auth (user, token) — persist vào `localStorage`.
- Cart (items) — lưu `localStorage`, sync khi cần.
- Notification/toast toàn cục.
- UI state (sidebar mở/đóng, theme).

**Local state → `useState`:**

- Form input, modal open, tab hiện tại.

### 6.3 Zustand pattern — bắt buộc

```typescript
// store/authStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  user: User | null;
  token: string | null;
  login: (user: User, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      login: (user, token) => set({ user, token }),
      logout: () => set({ user: null, token: null }),
    }),
    { name: 'auth-storage' }
  )
);
```

### 6.4 TanStack Query pattern — bắt buộc

```typescript
// Lấy data
const { data, isLoading, error } = useQuery({
  queryKey: ['products', { category }],
  queryFn: () => productApi.list({ category }),
});

// Mutation
const mutation = useMutation({
  mutationFn: productApi.create,
  onSuccess: () => {
    message.success('Thêm sản phẩm thành công');
    queryClient.invalidateQueries({ queryKey: ['products'] });
  },
  onError: (err) => {
    message.error(err.response?.data?.detail || 'Có lỗi xảy ra');
  },
});
```

### 6.5 Axios — 1 instance duy nhất

```typescript
// api/axios.ts
import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default api;
```

### 6.6 UI

- Dùng Ant Design components. KHÔNG tự viết CSS cho thứ AntD đã có.
- Layout dùng `Layout`, `Menu`, `Breadcrumb` của AntD.
- Form dùng `Form`, `Input`, `Select` của AntD.
- Bảng admin dùng `Table` với `pagination`, `filter`, `sorter`.
- Thông báo dùng `message` và `notification` của AntD.

### 6.7 Routing

| Path | Phân quyền |
|---|---|
| `/` | Public |
| `/products` | Public |
| `/products/:id` | Public |
| `/login` | Public |
| `/register` | Public |
| `/cart` | User |
| `/checkout` | User |
| `/orders` | User |
| `/orders/:id` | User |
| `/wishlist` | User |
| `/profile` | User |
| `/admin/*` | Admin (role = admin) |

- Bảo vệ route bằng `<ProtectedRoute>` (cần đăng nhập) và `<AdminRoute>` (cần role admin).

### 6.8 Files được phép AI viết

- Pages UI đơn giản, components tái sử dụng.
- Zustand stores (trừ `authStore`).
- TanStack Query hooks.
- AntD form components.

### 6.9 Files KHÔNG để AI viết (tự viết tay)

- `api/axios.ts` (interceptor, ảnh hưởng toàn app).
- `store/authStore.ts` (nhạy cảm bảo mật).
- `components/ProtectedRoute.tsx` và `components/AdminRoute.tsx`.
- Routing chính trong `App.tsx`.

## 7. Quy tắc Database

### 7.1 Bảng nghiệp vụ (schema `public`) — 8 bảng MVP

| Bảng | Cột chính |
|---|---|
| `users` | `id`, `email` UNIQUE, `password_hash`, `full_name`, `phone`, `address`, `avatar_url`, `role`, `is_active`, `created_at`, `updated_at` |
| `categories` | `id`, `name`, `slug` UNIQUE, `description`, `image_url`, `created_at`, `updated_at` |
| `brands` | `id`, `name`, `slug` UNIQUE, `logo_url`, `description`, `created_at`, `updated_at` |
| `products` | `id`, `name`, `slug` UNIQUE, `description`, `price`, `sale_price`, `stock`, `category_id` FK, `brand_id` FK, `skin_types` JSON, `concerns` JSON, `key_ingredients` JSON, `free_from` JSON, `variants` JSON, `sold_count`, `rating_avg`, `rating_count`, `is_active`, timestamps |
| `product_images` | `id`, `product_id` FK CASCADE, `public_id` UNIQUE, `secure_url`, `alt_text`, `width`, `height`, `format`, `position`, `is_main`, timestamps |
| `orders` | `id`, `user_id` FK, `order_code` UNIQUE, `status`, `subtotal`, `shipping_fee`, `discount`, `total`, `payment_method`, `payment_status`, `paid_at`, `transaction_id`, `shipping_name`, `shipping_phone`, `shipping_address`, `tracking_code`, `carrier`, `note`, timestamps |
| `order_items` | `id`, `order_id` FK CASCADE, `product_id` FK, `product_name`, `product_price`, `product_image`, `variant_info` JSON, `qty`, `subtotal` |
| `order_status_history` | `id`, `order_id` FK CASCADE, `status`, `note`, `created_by` FK, `created_at` |
| `wishlists` | `id`, `user_id` FK CASCADE, `product_id` FK CASCADE, `created_at`, UNIQUE(`user_id`, `product_id`) |

### 7.2 Quy tắc chung

- Mọi bảng có `id` (SERIAL PK) + `created_at`. Bảng có quan hệ thì có thêm `updated_at`.
- Dùng `TIMESTAMPTZ` cho mọi trường thời gian. KHÔNG dùng `TIMESTAMP` (không timezone).
- Foreign key có `ON DELETE CASCADE` khi phù hợp (vd: `order_items`, `order_status_history`, `wishlists`).
- Migration bằng Alembic. KHÔNG sửa DB thủ công.
- Tên bảng: snake_case số nhiều (`products`, `order_items`).
- Snapshot fields (`product_name`, `product_price`, `variant_info`) trong `order_items` KHÔNG tham chiếu động — lưu giá trị tại thời điểm mua.
- Soft delete: `is_active = false` thay vì `DELETE`. FK vẫn giữ nguyên.

### 7.3 Cấu trúc `variants` JSON

```json
[
  {
    "id": "v1",
    "name": "Đỏ Ruby",
    "price": 350000,
    "stock": 20,
    "image_url": "https://.../do-ruby.jpg"
  }
]
```

- `variants = null` → sản phẩm không có biến thể, dùng `price`/`stock` chính.
- `variants = [...]` → mỗi variant có giá/stock riêng.
- **Mỗi variant BẮT BUỘC có `id` + `name`**; `id` phải duy nhất trong 1 sản phẩm
  (cart key = `product_id` + `variant_id`); `price`/`stock` phải `>= 0`.
  BE validate bằng `VariantInfo` (`app/schemas/product.py`) → trả 400 nếu sai.
- Admin UI nhập biến thể qua `Form.List` (`pages/admin/Products.tsx`); `id` để trống → tự sinh.

**Quy tắc stock (1 nguồn sự thật):**

- Sản phẩm **không** có variants → `products.stock` là nguồn sự thật.
- Sản phẩm **có** variants → `variants[i].stock` là nguồn sự thật; `products.stock` là
  **giá trị dẫn xuat** = tổng stock các variants (KHÔNG trừ độc lập cả hai).
- Mọi logic stock nằm ở `app/service/product_stock.py` (`recompute_stock`, `effective_stock`).
- Sản phẩm có variants mà đơn không có `variant_id` → từ chối (tránh bán quá tồn kho).

## 8. API Conventions

### 8.1 URL

- Prefix `/api` cho mọi endpoint nghiệp vụ.
- Danh từ số nhiều: `/api/products`, `/api/orders`.
- Nested resource: `/api/orders/{id}/items`.
- Action đặc biệt: `/api/orders/{id}/cancel`, `/api/admin/orders/{id}/status`, `/api/payment/sepay-webhook`.

### 8.2 HTTP Methods

| Method | Mục đích |
|---|---|
| GET | Lấy dữ liệu, không side effect |
| POST | Tạo mới |
| PUT | Cập nhật toàn bộ |
| PATCH | Cập nhật một phần |
| DELETE | Xóa |

### 8.3 Pagination

- Query: `?page=1&size=20` (max `size = 100`).
- Response: `{ "data": [...], "total": 100, "page": 1, "size": 20, "message": "OK" }`.

### 8.4 Error codes

| Code | HTTP | Mô tả |
|---|---|---|
| `AUTH_INVALID` | 401 | Sai email/password |
| `TOKEN_EXPIRED` | 401 | Token hết hạn |
| `FORBIDDEN` | 403 | Không có quyền |
| `NOT_FOUND` | 404 | Không tìm thấy |
| `VALIDATION_ERROR` | 400 | Dữ liệu sai |
| `OUT_OF_STOCK` | 400 | Hết hàng |
| `INVALID_STATUS_TRANSITION` | 400 | Chuyển trạng thái sai |
| `PAYMENT_FAILED` | 400 | Thanh toán lỗi |
| `EMAIL_EXISTS` | 400 | Email đã tồn tại |
| `ACCOUNT_LOCKED` | 403 | Tài khoản bị khóa |

## 9. Quy tắc nghiệp vụ quan trọng

### 9.1 Auth

- Email format hợp lệ, unique.
- Password tối thiểu 6 ký tự, hash bằng bcrypt cost 12.
- `is_active = false` → không cho đăng nhập (403 `ACCOUNT_LOCKED`).

### 9.2 Product

- Filter: `category_id`, `brand_id`, `min_price`, `max_price`, `skin_types[]`, `concerns[]`, `search`, `sort`.
- Sort: `price_asc | price_desc | newest | best_seller`.
- Chỉ trả sản phẩm `is_active = true` cho public API.
- Variants lưu JSON; nếu có variant → dùng giá/stock variant khi tính tiền và trừ stock.

### 9.3 Cart (FE only)

- Zustand + `localStorage`.
- KHÔNG có endpoint BE cho cart.
- Check stock khi checkout (BE mới kiểm tra).

### 9.4 Checkout

- Validate: items không rỗng, variant tồn tại, stock đủ, phone VN format, address không rỗng.
- Snapshot giá vào `order_items` (không tham chiếu động).
- Order code format: `<SEPAY_PAYMENT_CODE_PREFIX>` (mặc định `ORD`) + `YYYYMMDD` + 4 số random
  (vd: `ORD202609200013`) — tổng hậu tố = `SEPAY_PAYMENT_CODE_SUFFIX_LENGTH` (mặc định `12`) chữ số.
  - **Phải khớp 100% với mẫu mã thanh toán khai báo trên dashboard SePay**
    (Công ty → Cấu hình chung → Cấu trúc mã thanh toán: tiền tố `ORD`, hậu tố 12 số).
    Lệch ⇒ SePay không trích được `code` ⇒ **không gửi webhook** ⇒ mất tiền, đơn kẹt `unpaid`.
  - Nguồn sự thật duy nhất: `backend/app/payment/payment_code.py` (regex + validate + sinh mã).
    Đổi format chỉ sửa config + cập nhật mẫu trên dashboard SePay.
- Shipping fee mặc định `30.000đ`, miễn phí nếu `subtotal ≥ 500.000đ`.
- Trừ stock trong transaction. Rollback nếu có lỗi bất kỳ.
- SePay: trả QR URL `https://vietqr.app/img?acc=...&bank=...&amount=...&des=ORDER_CODE`.
  - `amount` luôn là số nguyên VND (ep `int` từ `Decimal`, tránh `430000.0` / `1.00E+6`).
  - `des` có thể cần tiền tố bắt buộc (`SEVQR` với VietinBank cá nhân) → `SEPAY_QR_CONTENT_PREFIX`.
    Tiền tố này **khác** tiền tố mã thanh toán (`ORD`) — SePay quét toàn bộ nội dung nên vẫn thấy mã.
  - Fail-fast: `create_payment_link` raise nếu `order_code` không khớp mẫu SePay (không sinh QR sai).

### 9.5 Order state machine

```text
pending   --confirmed | cancelled--> confirmed | cancelled
confirmed --packing   | cancelled--> packing   | cancelled
packing   --shipping                --> shipping
shipping  --delivered               --> delivered
delivered, cancelled = final
```

- Hủy đơn: chỉ khi `pending | confirmed`, hoàn stock.
- Chuyển trạng thái sai → 400 `INVALID_STATUS_TRANSITION`.

### 9.6 SePay webhook

- Verify HMAC-SHA256 (`X-SePay-Signature` + `X-SePay-Timestamp`) nếu có `SEPAY_WEBHOOK_SECRET`;
  fallback `Authorization: Apikey <SEPAY_KEY>`.
- Extract `order_code` từ `code`/`subAccount`/`content` bằng regex **động** dựng từ
  `SEPAY_PAYMENT_CODE_PREFIX` + `SEPAY_PAYMENT_CODE_SUFFIX_LENGTH` (mặc định `ORD\d{12}`).
- **Idempotent:** nếu đã `paid` → skip update.
- Order không tồn tại → vẫn trả `{success: true}` để SePay không retry.
- Khoá chống trùng = `referenceCode` (mã tham chiếu ngân hàng), fallback `str(id)`.
  `id` khác nhau giữa webhook (int) và API v2 (UUID) ⇒ dùng `id` sẽ vô hiệu hoá unique index.
- Sai tài khoản nhận (`accountNumber` ≠ `SEPAY_BANK_ACCOUNT`, so sánh đã bỏ số 0 đầu) → log `wrong_account`, KHÔNG đánh paid.
- Đối soát (`POST /api/payment/reconcile`): quét SePay API v2 `/transactions` (có phân trang).
  - `transaction_date_to` là **exclusive** ⇒ phải dùng `hôm nay + 1 ngày`, nếu không sẽ luôn `scanned = 0`.
  - Dùng **cùng khoá** `reference_number` ⇒ không đánh paid trùng với webhook.
- **Chống trùng ở 2 tầng** (bắt buộc cả hai):
  - Tầng app: `update_payment_status()` check `Order.transaction_id` trước khi ghi.
  - Tầng DB: unique index `uq_orders_transaction_id` (partial, `transaction_id IS NOT NULL`)
    + `uq_payment_webhook_provider_txid`.
  - Tầng app **không đủ**: 2 request song song (webhook + reconcile) cùng 1 giao dịch đều đọc
    "không thấy duplicate" trước khi ghi ⇒ cả 2 đơn cùng `paid` ⇒ cộng tiền 2 lần.
    Unique index DB là chốt chặn cuối cùng.
  - Migration `f4a5b6c7d8e9` tạo index idempotent (`IF NOT EXISTS`) vì DB có thể được
    tạo bởi `create_all` (bỏ sót constraint) thay vì alembic.

### 9.6.1 Fail-fast lúc start app

`app/payment/payment_config_check.py` chạy trong `lifespan` của `app.main` →
app **không start** nếu cấu hình thanh toán sai. Lý do: cấu hình sai chỉ lộ ra
khi có giao dịch thật ⇒ tiền vào tài khoản nhưng đơn kẹt `unpaid` (mất tiền im lặng).

- **Chặn start (raise):**
  - `SEPAY_PAYMENT_CODE_PREFIX` phải 2–5 ký tự (quy định SePay).
  - `SEPAY_PAYMENT_CODE_SUFFIX_LENGTH` phải 1–30.
  - Tổng độ dài mã ≤ 32 (giới hạn cột `orders.order_code`).
  - Nếu `SEPAY_BANK_NAME = ICB` (VietinBank) ⇒ `SEPAY_QR_CONTENT_PREFIX` phải chứa `SEVQR`.
    VietinBank cá nhân bắt buộc `SEVQR` trong nội dung CK; thiếu ⇒ SePay **không** đẩy
    giao dịch về webhook ⇒ mất tiền.
- **Chỉ cảnh báo (app vẫn start):** thiếu `SEPAY_BANK_ACCOUNT` / `SEPAY_WEBHOOK_SECRET` / `SEPAY_API_TOKEN`.

### 9.7 Admin tracking

- Update `order.status` + insert `order_status_history`.
- Sinh `tracking_code` giả khi status → `shipping` (nếu chưa có).
- COD: status → `delivered` → tự động `payment_status = paid`.

### 9.8 Routine Builder

- Input: `skin_type`, `concerns[]`, `budget`, `age`, `allergies[]`.
- Query product match:
  - `skin_types` chứa `skin_type`.
  - `concerns` overlap với input concerns.
  - `price ≤ budget / 4` (mỗi bước tối đa 1/4 ngân sách).
  - `free_from` không chứa `allergies`.
- BE gọi AI `/routine` → trả `steps` + `note`.
- FE hiển thị routine, user nhấn "Thêm tất cả vào giỏ".

## 10. Docker & môi trường

### 10.1 docker-compose — 5 services

| Service | Port | Image / Build |
|---|---|---|
| `postgres` | 5432 | `postgres:17-alpine` |
| `adminer` | 8080 | `adminer:latest` |
| `backend` | 8000 | build từ `./backend` |
| `ai` | 8001 | build từ `./ai` |
| `fe` | 3000 | build từ `./fe` |

### 10.2 Quy tắc

- Dev chạy `--reload` (uvicorn) hoặc `npm run dev` (Vite).
- Volume mount code để hot reload.
- Biến môi trường đọc từ `.env`. KHÔNG hardcode.
- `.env.example` có đủ key mẫu, `.env` KHÔNG commit.
- Webhook SePay local: **cloudflared tunnel** (khuyên dùng) hoặc `ngrok`.

### 10.3 Biến môi trường (tóm tắt)

Xem chi tiết tại [03-tech-stack.md §4](03-tech-stack.md).

```dotenv
POSTGRES_DB=cosme_shop
POSTGRES_USER=admin
POSTGRES_PASSWORD=secret
DATABASE_URL=postgresql+asyncpg://admin:secret@postgres:5432/cosme_shop
JWT_SECRET_KEY=change-me
ACCESS_TOKEN_EXPIRE_SECONDS=86400
SEPAY_API_KEY=
SEPAY_BANK_ACCOUNT=
SEPAY_BANK_NAME=
AI_SERVICE_URL=http://ai:8001
GEMINI_API_KEY=
LLM_PROVIDER=gemini
VITE_API_URL=http://localhost:8000
```

## 11. Quy tắc chung cho Cursor

### 11.1 Khi sinh code

- LUÔN kiểm tra mục 2 (Stack) trước khi gợi ý thư viện.
- KHÔNG thêm dependency mới nếu chưa có trong `requirements.txt` hoặc `package.json` đã duyệt.
- KHÔNG dùng TypeScript `any`. KHÔNG dùng class component. KHÔNG dùng `var`.
- KHÔNG dùng Python `Any` — dùng type cụ thể hoặc `Optional[T]`.
- Trả code ngắn gọn, có comment tiếng Việt cho phần logic phức tạp.
- File không quá 200 dòng — tách nhỏ khi cần.

### 11.2 Khi refactor

- Giữ nguyên public API contract (URL, request/response format).
- Không đổi tên file trừ khi được yêu cầu.
- Chạy test (nếu có) trước khi đề xuất.

### 11.3 Khi gặp ambiguity

- Hỏi lại thay vì tự quyết định thêm thư viện hoặc đổi kiến trúc.
- Ưu tiên giải pháp đơn giản nhất chạy được.

### 11.4 Ngôn ngữ

- Comment trong code: tiếng Việt.
- Tên biến/hàm/class: tiếng Anh.
- Message trả về cho user: tiếng Việt.
- Commit message: tiếng Anh, format Conventional Commits (`feat:`, `fix:`, `chore:`).

## 12. Git Conventions

- Branch chính: `main`.
- Branch tính năng: `feat/<ten-tinh-nang>`, `fix/<ten-bug>`.
- Commit: `feat(backend): add product CRUD`, `fix(fe): cart total wrong`.
- KHÔNG commit `.env`, `node_modules`, `__pycache__`, `.venv`, `dist`, `*.pyc`, `*.sqlite3`.
- File `.gitignore` phải có đủ các mục trên.
- Pre-commit: chạy lint. Pre-push: chạy test (KHÔNG bỏ qua test fail).

## 13. Testing & Quality

### 13.1 Backend

- `pytest` + `pytest-asyncio` + `httpx.AsyncClient` (TestClient async).
- Test cho core flow: auth (register/login), product CRUD, checkout, order state transition, SePay webhook idempotency.
- Coverage tối thiểu 60% cho `service/` layer.
- KHÔNG mock cheating — test phải là code thật, dùng test DB hoặc transaction rollback.

### 13.2 Frontend

- `vitest` + `@testing-library/react`.
- Test cho store Zustand (login/logout, cart add/remove).
- Test cho hook TanStack Query quan trọng.
- KHÔNG mock toàn bộ component — chỉ mock network layer.

### 13.3 Lint & Format

- Backend: `ruff check` + `ruff format` (ưu tiên) hoặc `flake8 + black`.
- Frontend: `eslint .` (theo `eslint.config.js`) + `tsc --noEmit`.

## 14. Ưu tiên khi hết thời gian

Nếu trễ tiến độ, cắt theo thứ tự sau:

1. Bỏ wishlist.
2. Bỏ mã giảm giá (chỉ giữ thanh toán cơ bản).
3. Bỏ filter nâng cao ở FE (chỉ giữ search theo tên).
4. Đơn giản hóa admin (chỉ CRUD cơ bản, bỏ dashboard thống kê).
5. **KHÔNG BAO GIỜ CẮT:** auth, product, cart, order, payment (COD + SePay), Routine Builder Quiz.

## 15. Checklist trước khi demo

- `docker compose up` chạy được từ máy sạch.
- Đăng ký → đăng nhập → thêm sản phẩm vào giỏ → đặt hàng → thanh toán COD.
- Đặt hàng SePay → webhook cập nhật `payment_status = paid`.
- Admin CRUD sản phẩm có variants, xem đơn, cập nhật trạng thái.
- Routine Builder Quiz trả về steps hợp lệ.
- Không có lỗi console ở FE.
- Có seed data trong DB.
- `.env.example` có đủ key, README hướng dẫn chạy.

## Phụ lục — Phát hiện quan trọng khi review

Khi review code, các vấn đề dưới đây đã được phát hiện và cần xử lý trong plan implementation riêng (xem [01-system-design.md](01-system-design.md) để biết context):

- `User` model trong `backend/app/model/user.py` đang dùng `username`/`password` (plain) — cần đổi sang `email`/`password_hash` (bcrypt).
- `db/base.py` và `db/session.py` đang khai báo 2 class `Base` khác nhau → Alembic không thấy schema. Phải enforce "Singleton Base" theo mục 4.3.
- Hầu hết file trong `api/`, `service/`, `core/security.py`, `main.py` đang rỗng — cần implement theo cấu trúc ở mục 3.
- Folder `/ai` chưa tồn tại — cần scaffold theo mục 3.
- Chưa có `docker-compose.yml` — cần tạo theo mục 10.1.
