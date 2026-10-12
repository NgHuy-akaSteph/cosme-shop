# Phase 04: UAT Checklist — 3 Personas

## Context Links

- [plan.md](plan.md) — Overview
- [phase-01-fix-backend-blockers.md](phase-01-fix-backend-blockers.md) — Prerequisite
- [phase-02-fix-frontend-build.md](phase-02-fix-frontend-build.md) — Prerequisite
- [phase-03-seed-and-smoke-test.md](phase-03-seed-and-smoke-test.md) — Prerequisite (seed & smoke test data OK)
- [docs/02-business-requirement.md](../../docs/02-business-requirement.md) — Section 7: Demo scenarios
- [docs/04-database.md](../../docs/04-database.md) — Section 11: Seed data specs

## Overview

- **Priority**: P1 (final phase of UAT readiness)
- **Status**: Complete
- **Brief**: Define concrete test cases covering 3 personas (Guest, Customer, Admin) with pass/fail criteria. Use seed data from Phase 03.

## Key Insights

### 3 Personas

1. **Guest (anonymous)** — Browse, xem chi tiết sản phẩm, làm Routine Quiz
2. **Customer (`user@cosme-shop.com` / `user123`)** — Register, login, wishlist, cart, checkout, order tracking
3. **Admin (`admin@cosme-shop.com` / `admin123`)** — CRUD sản phẩm, quản lý orders, xem dashboard

### Seed Data Available

- 2 users (admin + test user)
- 8 categories
- 5 brands
- 20 products với ProductImage + JSONB metadata (skin_types, concerns, key_ingredients, free_from)
- 0 orders/wishlist (sạch sẽ)

### Demo Accounts

| Role | Email | Password | Scope |
|---|---|---|---|
| Admin | `admin@cosme-shop.com` | `admin123` | Full access |
| Customer | `user@cosme-shop.com` | `user123` | Standard user |

## Requirements

### Functional
- Mỗi test case có step-by-step actions + expected result
- Cover 3 personas: Guest, Customer, Admin
- Cover full happy path: register → browse → cart → checkout → order tracking
- Cover edge cases: empty cart, invalid login, out-of-stock

### Non-Functional
- Pass criteria rõ ràng cho mỗi case (status code + UI state)
- Mỗi persona có ~10-15 test cases
- Format: checkable list để tester tick

## Related Code Files

### Read for context
- `frontend/src/pages/` — Tất cả pages
- `frontend/src/components/` — Layout, ProtectedRoute, AdminRoute
- `backend/app/api/` — Tất cả endpoints
- `docs/02-business-requirement.md` — Demo scenarios

### No modify
- Phase 04 chỉ tạo checklist, KHÔNG modify code

## Implementation Steps

### Step 4.1: Inventory frontend pages & routes

Liệt kê tất cả pages/routes để biết coverage cần test:

```bash
ls frontend/src/pages/
ls frontend/src/pages/user/
ls frontend/src/pages/admin/
grep -r "Route path=" frontend/src/App.tsx
```

### Step 4.2: Inventory backend endpoints

```bash
ls backend/app/api/
grep -E "router\.(get|post|patch|delete|put)" backend/app/api/*.py
```

### Step 4.3: Test infrastructure setup

- Verify backend đang chạy: `curl http://localhost:8000/health`
- Verify frontend đang chạy: `curl http://localhost:5173`
- Verify DB có seed data: truy vấn count products/categories/users
- Reset nếu cần: chạy lại seed script

### Step 4.4: Viết checklist cho Guest persona (~8 cases)

1. Browse products list (filter by category/brand/skin_type)
2. Xem product detail (có ảnh, giá, ingredients)
3. Tìm kiếm sản phẩm
4. Sort products (price asc/desc, newest, best-seller)
5. Xem best-sellers
6. Xem similar products
7. Làm Routine Quiz (gửi quiz → nhận routine steps)
8. Xem categories list, click vào category

### Step 4.5: Viết checklist cho Customer persona (~15 cases)

Auth flow:
1. Register với email mới
2. Login với email/password đúng
3. Login sai password → 401
4. Register với email đã tồn tại → 400
5. Access /profile khi chưa login → redirect /login
6. Logout

Profile:
7. Xem profile của mình
8. Update profile (full_name, phone, address)
9. Change password

Wishlist:
10. Add product vào wishlist
11. View wishlist
12. Remove khỏi wishlist

Cart & Checkout:
13. Add to cart (nếu frontend có cart UI)
14. Update cart item qty
15. Remove cart item
16. Checkout: điền shipping info, payment method = COD
17. Order created → redirect /orders hoặc /order-success
18. Xem order list của tôi
19. Xem order detail (status timeline)

### Step 4.6: Viết checklist cho Admin persona (~15 cases)

Auth:
1. Login admin → access /admin
2. Customer truy cập /admin → 403/redirect

Dashboard:
3. Xem stats (orders count, revenue, products count)
4. Xem recent orders

Products CRUD:
5. List all products (admin view)
6. Create product mới (form: name, slug, price, category, brand, images, JSON fields)
7. Edit product (update price, sale_price, stock)
8. Soft-delete product (is_active = false)
9. Hard-delete product (cascade images)

Categories/Brands:
10. Create category mới
11. Edit category
12. Delete category (cascade products nếu có)

Orders management:
13. List all orders (admin)
14. Xem order detail
15. Update order status (pending → confirmed → shipping → delivered)
16. Add status history note

### Step 4.7: Viết cross-cutting test cases (~5 cases)

- Security: user A không thấy order của user B
- Validation: required fields missing → 400
- Pagination: products?page=2&size=5 hoạt động
- Image upload: POST /api/upload → Cloudinary URL
- 404 cases: /api/products/9999 → 404

### Step 4.8: Format checklist thành test file

Output `phase-04-uat-checklist.md` chứa bảng Markdown checkable với:
- Persona | Test ID | Action | Expected Result | Pass/Fail

### Step 4.9: Smoke check trước khi đưa cho tester

```bash
# Backend health
curl http://localhost:8000/api/products?size=1
# Frontend health
curl http://localhost:5173
# Admin login roundtrip
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@cosme-shop.com","password":"admin123"}'
```

## Todo List

- [x] Step 4.1: Inventory frontend pages & routes (18 pages, 21 routes)
- [x] Step 4.2: Inventory backend endpoints (28 endpoints across 10 routers)
- [x] Step 4.3: Test infrastructure setup (DB seed OK, backend OK, JSONB verified)
- [x] Step 4.4: Guest persona checklist (12 cases)
- [x] Step 4.5: Customer persona checklist (18 cases)
- [x] Step 4.6: Admin persona checklist (16 cases)
- [x] Step 4.7: Cross-cutting test cases (8 cases)
- [x] Step 4.8: Format checklist as test file → `reports/uat-checklist.md`
- [x] Step 4.9: Pre-flight smoke check → ALL PASS

## Success Criteria

- ✅ Checklist covers tất cả routes/endpoints identified ở Step 4.1 + 4.2
- ✅ 3 personas đầy đủ: Guest, Customer, Admin
- ✅ Mỗi test case có clear pass/fail criteria
- ✅ File format dễ cho tester tick (markdown checkbox + bảng)
- ✅ Pre-flight smoke check PASS

## Risk Assessment

### Risk 1: Frontend pages chưa implement

- Mitigation: Inventory step 4.1 sẽ phát hiện; note "N/A" cho cases chưa có UI.

### Risk 2: Cloudinary upload không available

- Mitigation: Test upload qua mock URL hoặc skip nếu service down.

### Risk 3: AI service chưa chạy

- Mitigation: Routine Quiz test case chấp nhận 200 (success) hoặc 503 (AI offline) per phase-03.

### Risk 4: Email confirm flow chưa có

- Mitigation: Checklist ghi rõ "register → auto-login" (no email confirm step).

## Security Considerations

- Test KHÔNG commit test data với real PII
- Test KHÔNG dùng production DB
- Test KHÔNG log password ra console

## Next Steps

Sau khi Phase 04 done → deliver checklist cho tester team chạy UAT session.
Track issues → tạo `phase-05-fix-uat-issues.md` nếu phát hiện bugs trong UAT.
