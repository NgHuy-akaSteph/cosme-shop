# cosme-shop Implementation Plan — 5 Tuần

> Trạng thái: **Tuần 1-4 Hoàn thành** | Tuần 5/5 (in progress)

---

## Tuần 1: Foundation & Backend Core ✅

### Phase 1.1: Setup Infrastructure ✅
- [x] Tạo `docker-compose.yml` với 4 services (postgres:17-alpine, adminer, backend, fe) — AI service đã loại bỏ
- [x] Tạo `.env.example` đầy đủ các biến môi trường
- [x] Cấu hình Alembic cho migration
- [x] Fix "Singleton Base" trong `backend/app/db/session.py` — import từ `base.py`
- [x] Fix `backend/app/model/user.py` — đổi sang schema đúng (email, password_hash, full_name, phone, address, role, is_active)

### Phase 1.2: Database Models ✅
- [x] Tạo `backend/app/model/category.py` — categories table
- [x] Tạo `backend/app/model/brand.py` — brands table
- [x] Tạo `backend/app/model/product.py` — products table với JSON columns
- [x] Tạo `backend/app/model/order.py` — orders table
- [x] Tạo `backend/app/model/order_item.py` — order_items table
- [x] Tạo `backend/app/model/order_status_history.py` — timeline table
- [x] Tạo `backend/app/model/wishlist.py` — wishlists table
- [x] Chạy Alembic migration để tạo schema

### Phase 1.3: Auth Foundation ✅
- [x] Implement `backend/app/core/security.py` — JWT, bcrypt functions
- [x] Implement `backend/app/api/deps.py` — get_current_user, get_current_admin dependencies
- [x] Implement `backend/app/api/auth.py` — register, login, me, change-password endpoints
- [x] Implement `backend/app/service/auth_service.py` — auth business logic
- [x] Implement `backend/app/service/user_service.py` — user CRUD
- [x] Tạo `backend/app/main.py` với exception handlers và startup events

### Phase 1.4: Seed Data ✅
- [x] Tạo `backend/app/scripts/seed.py` — script tạo sample data
- [x] Seed: 1 admin, 1 user, 5 categories, 5 brands, 20-30 products

**Deliverable Tuần 1:** Backend chạy được, API auth hoạt động, có data để test ✅

---

## Tuần 2: Backend APIs ✅

### Phase 2.1: Product APIs ✅
- [x] Tạo `backend/app/schemas/product.py` — Pydantic schemas
- [x] Implement `backend/app/service/product_service.py` — CRUD, filter, search
- [x] Implement `backend/app/api/products.py` — public + admin endpoints
- [x] Tạo `backend/app/schemas/category.py` và `brand.py`
- [x] Implement `backend/app/api/categories.py` — CRUD admin + list public
- [x] Implement `backend/app/api/brands.py` — CRUD admin + list public

### Phase 2.2: Order APIs ✅
- [x] Tạo `backend/app/schemas/order.py` — Pydantic schemas
- [x] Implement `backend/app/service/order_service.py` — checkout, cancel, state transitions
- [x] Implement `backend/app/api/orders.py` — user orders, cancel
- [x] Implement `backend/app/api/admin.py` — admin order management

### Phase 2.3: Payment (COD) ✅
- [x] COD integration — không cần webhook, payment_status updated khi admin confirm

### Phase 2.4: Wishlist ✅
- [x] Implement `backend/app/api/wishlist.py` — CRUD endpoints
- [x] Implement `backend/app/service/wishlist_service.py`

**Deliverable Tuần 2:** Full CRUD APIs hoạt động, order flow hoàn chỉnh ✅

---

## Tuần 3: Cloudinary Storage ✅ (mới)

### Phase 3.0: Cloudinary Setup & Integration ✅
- [x] Tạo Cloudinary account, lấy credentials (cloud_name, api_key, api_secret)
- [x] Tạo unsigned upload preset `cosme_shop_unsigned` (folder: `cosme-shop/products`)
- [x] Thêm `cloudinary==1.41.0` vào `backend/requirements.txt`
- [x] Thêm `@cloudinary/url-gen`, `@cloudinary/react` vào `frontend/package.json`
- [x] Cập nhật `.env` và `.env.example` với Cloudinary vars

### Phase 3.1: Backend Cloudinary Service ✅
- [x] Tạo `backend/app/core/cloudinary.py` — wrapper service (upload_image, delete_image, get_optimized_url)
- [x] Tạo `backend/app/schemas/upload.py` — Pydantic schemas
- [x] Tạo `backend/app/api/upload.py` — POST `/api/upload/image`, DELETE `/api/upload/image/{public_id}` (admin only)
- [x] Mount upload router trong `backend/app/main.py`
- [x] Validate: image type only, max 5MB, authenticated admin

### Phase 3.2: Frontend Upload Component ✅
- [x] Tạo `frontend/src/lib/cloudinary.ts` — Cloudinary client instance
- [x] Tạo `frontend/src/components/admin/ImageUploader.tsx` — Ant Design Upload widget với direct upload
- [x] Tích hợp ImageUploader vào `frontend/src/pages/admin/ProductFormPage.tsx`
- [x] Lưu `images` vào DB dạng JSON `[{public_id, url}]`
- [x] Update `.env` FE với `VITE_CLOUDINARY_CLOUD_NAME`, `VITE_CLOUDINARY_UPLOAD_PRESET`

### Phase 3.3: Image Optimization ✅
- [x] Sử dụng Cloudinary URL transformation trong `ProductCard`, `ProductDetail` (auto format WebP, auto quality)
- [x] Thumbnail URLs (300x300), gallery URLs (800x800), detail URLs (1200+)
- [x] Verify CDN caching hoạt động

**Deliverable Tuần 3:** Ảnh sản phẩm upload lên Cloudinary CDN, tối ưu tự động, miễn phí ✅

---

## Tuần 4: Frontend ✅

### Phase 4.1: Setup & Auth ✅
- [x] Cài đặt dependencies: react-router-dom, @tanstack/react-query, zustand, axios, antd
- [x] Setup `frontend/src/api/axios.ts` — Axios instance với interceptors
- [x] Setup `frontend/src/store/authStore.ts` — Zustand auth store
- [x] Setup `frontend/src/store/cartStore.ts` — Zustand cart store
- [x] Implement `frontend/src/components/ProtectedRoute.tsx` và `AdminRoute.tsx`
- [x] Implement Auth pages: Login, Register

### Phase 4.2: Public Pages ✅
- [x] Implement `frontend/src/pages/HomePage.tsx` — hero, best-sellers
- [x] Implement `frontend/src/pages/ProductsPage.tsx` — list với filter
- [x] Implement `frontend/src/pages/ProductDetailPage.tsx` — chi tiết sản phẩm

### Phase 4.3: User Pages ✅
- [x] Implement Cart page (Zustand)
- [x] Implement Checkout page — COD + SePay
- [x] Implement Orders page — danh sách đơn
- [x] Implement OrderDetailPage — timeline
- [x] Implement Wishlist page
- [x] Implement Profile page

### Phase 4.4: Admin Pages ✅
- [x] Admin layout với sidebar
- [x] Admin Dashboard
- [x] Admin Product CRUD — form với variants
- [x] Admin Order management — filter, status update
- [x] Admin Category & Brand CRUD
- [x] Admin User management

**Deliverable Tuần 4:** Full working frontend, có thể demo end-to-end ✅

---

## Tuần 5: SePay

### Phase 5.1: SePay Integration
- [ ] Implement `backend/app/api/payment.py` — SePay webhook endpoint
- [ ] Implement `backend/app/service/payment_service.py` — QR generation, idempotent handling
- [ ] Cấu hình Cloudflare Tunnel cho webhook testing (manual step)

### Phase 5.2: Testing & Documentation (ongoing)
- [ ] Backend: pytest cho service layer (auth, product, order)
- [ ] Frontend: vitest cho Zustand stores
- [ ] Integration testing cho critical flows
- [ ] Chạy checklist demo (xem docs)
- [ ] Update README với hướng dẫn chạy
- [ ] Commit và push code

**Deliverable Tuần 5:** SePay thanh toán hoàn chỉnh, full documentation ✅

---

## Files đã tạo/sửa chính

### Backend (tạo mới)
- `backend/app/model/category.py` ✅
- `backend/app/model/brand.py` ✅
- `backend/app/model/product.py` ✅
- `backend/app/model/order.py` ✅
- `backend/app/model/order_item.py` ✅
- `backend/app/model/order_status_history.py` ✅
- `backend/app/model/wishlist.py` ✅
- `backend/app/schemas/*.py` (auth, user, product, category, brand, order, wishlist, upload) ✅
- `backend/app/service/*.py` (auth, user, product, order, payment, wishlist) ✅
- `backend/app/api/*.py` (auth, users, products, categories, brands, orders, payment, wishlist, admin, upload) ✅
- `backend/app/core/security.py` ✅
- `backend/app/core/cloudinary.py` ✅ (Tuần 3)
- `backend/app/main.py` ✅
- `backend/app/scripts/seed.py` ✅
- `backend/alembic/` ✅

### Backend (sửa)
- `backend/app/model/user.py` ✅
- `backend/app/db/session.py` ✅
- `backend/app/core/config.py` ✅

### AI Service (đã loại bỏ)
<!-- Tính năng AI (Routine Builder) đã được loại bỏ khỏi scope dự án.
     Folder `ai/` trong repo chỉ còn Dockerfile + requirements.txt + .env rỗng.
     Endpoint `/api/ai/routine` đã được ngừng phát triển.
-->

### Frontend (tạo mới)
- `frontend/src/api/axios.ts` ✅
- `frontend/src/store/authStore.ts` ✅
- `frontend/src/store/cartStore.ts` ✅
- `frontend/src/components/*.tsx` (ProtectedRoute, AdminRoute, MainLayout, AdminLayout, ImageUploader) ✅
- `frontend/src/pages/*.tsx` (tất cả pages) ✅
- `frontend/src/lib/cloudinary.ts` ✅ (Tuần 3)
- `frontend/src/App.tsx` ✅

### Root (tạo mới)
- `docker-compose.yml` ✅
- `.env.example` ✅

---

## Dependencies cài

### Backend (requirements.txt)
```
fastapi, uvicorn[standard], sqlalchemy[asyncio], asyncpg, alembic
pydantic, pydantic-settings, python-jose[cryptography], passlib[bcrypt]
python-multipart, httpx, python-dotenv
cloudinary==1.41.0  # Tuần 3
```

### Frontend (package.json bổ sung)
```
react-router-dom, @tanstack/react-query, zustand, axios, antd
@cloudinary/url-gen, @cloudinary/react  # Tuần 3
```

### AI Service (đã loại bỏ)
<!-- Không còn AI service trong scope. Folder `ai/` chỉ còn skeleton. -->

---

## Risk Mitigation

| Rủi ro | Mitigation |
|---------|------------|
| Hết thời gian | Cắt theo thứ tự: Wishlist → SePay → Admin features |
| SePay webhook khó test | Dùng Cloudflare Tunnel, test manual với sandbox |
| DB migration lỗi | Review migration trước commit, rollback plan sẵn sàng |
| Cloudinary quota vượt free tier | 25 credits/tháng — dùng `q_auto,f_auto` transform để tiết kiệm |
| Unsigned upload bị abuse | Validate max 5MB, dùng upload preset với allowed formats |

---

## Success Criteria

1. `docker compose up` chạy được từ máy sạch ✅
2. Đăng ký → đăng nhập → thêm giỏ → đặt hàng COD hoàn chỉnh ✅
3. SePay webhook cập nhật payment_status
4. Admin CRUD sản phẩm với variants ✅
5. Không có lỗi console nghiêm trọng ở FE ✅
6. Có seed data để demo ✅
7. Upload ảnh sản phẩm lên Cloudinary CDN thành công ✅
8. Image transformation (resize, webp auto) hoạt động ✅
9. Tổng chi phí cloud storage < 0đ (free tier) ✅

---

## Next Steps

1. Chạy `docker compose up` để khởi động
2. Chạy migration: `docker compose exec backend alembic upgrade head`
3. Seed data: `docker compose exec backend python -m app.scripts.seed`
4. Cài frontend dependencies: `cd frontend && npm install`
5. Cấu hình Cloudinary: lấy credentials → cập nhật `.env` backend + frontend
6. Test upload ảnh từ admin UI
7. Test các API endpoints
8. Tuần 5: implement SePay (xem plan `cloud_storage_implementation_plan_62c31343.plan.md` chi tiết Cloudinary)
