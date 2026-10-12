# UAT Checklist — cosme-shop

> **Status**: Ready for execution
> **Last updated**: 2026-10-13
> **Owner**: QA team
> **Environment**: Dev (Neon PostgreSQL, seed data loaded)

## Pre-flight

| # | Check | Expected | Status |
|---|---|---|---|
| 0.1 | Backend running at `http://localhost:8000` | `GET /api` → 200 | ☐ |
| 0.2 | Frontend running at `http://localhost:5173` | HTTP 200 | ☐ |
| 0.3 | DB has seed data | products ≥ 20, categories ≥ 5, brands ≥ 5, users = 2 | ☐ |
| 0.4 | Admin can login | `POST /api/auth/login` returns 200 | ☐ |
| 0.5 | JSONB columns work | `?skin_types=oily` filters correctly | ☐ |
| 0.6 | Frontend build OK | `npm run build` exit 0 | ☐ |

## Demo Accounts

| Role | Email | Password |
|---|---|---|
| Admin | `admin@cosme-shop.com` | `admin123` |
| Customer | `user@cosme-shop.com` | `user123` |

## Test Conventions

- ✅ = Pass
- ❌ = Fail (note issue + screenshot)
- ⏸ = Blocked (note blocker)
- 🟡 = Pass with workaround

---

## 1. Guest Persona (Anonymous) — 12 cases

| # | Test ID | Action | Expected Result | Pass |
|---|---|---|---|---|
| 1.1 | G-HOME | Visit `/` | HomePage renders with hero + featured products | ☐ |
| 1.2 | G-LIST | Visit `/products` | Product list with 20 products, pagination works | ☐ |
| 1.3 | G-FILTER-CAT | Click category "Skincare" | List filtered to Skincare products only | ☐ |
| 1.4 | G-FILTER-BRAND | Click brand "The Ordinary" | List filtered to that brand | ☐ |
| 1.5 | G-SORT | Sort by "Giá tăng dần" | Products sorted ascending by price | ☐ |
| 1.6 | G-SEARCH | Search keyword "serum" | Only products with "serum" in name show | ☐ |
| 1.7 | G-BEST | Visit `/products` Best Sellers section | Top 4-10 best sellers shown | ☐ |
| 1.8 | G-DETAIL | Click any product | Detail page shows name, price, image, description, ingredients | ☐ |
| 1.9 | G-SIMILAR | On detail page, scroll to "Similar" | 4-8 similar products from same category | ☐ |
| 1.10 | G-QUIZ | Visit `/routine`, fill quiz (oily, acne, 5M VND) | Routine results with steps OR "no products match budget" | ☐ |
| 1.11 | G-CAT-PAGE | Visit `/products?category_id=1` | URL filter applies, only that category | ☐ |
| 1.12 | G-404-PROD | Visit `/products/99999` | 404 page or empty state | ☐ |

---

## 2. Customer Persona (Logged-in User) — 18 cases

### 2.1 Auth Flow

| # | Test ID | Action | Expected Result | Pass |
|---|---|---|---|---|
| 2.1.1 | C-REG-OK | Register with new email `uat1@test.com` | 201, auto-login, redirect home | ☐ |
| 2.1.2 | C-REG-DUP | Register with `admin@cosme-shop.com` | 400, error "Email đã tồn tại" | ☐ |
| 2.1.3 | C-REG-WEAK | Register password "123" | 400, error "Mật khẩu ≥ 6 ký tự" | ☐ |
| 2.1.4 | C-LOGIN-OK | Login `user@cosme-shop.com` / `user123` | 200, token stored, redirect | ☐ |
| 2.1.5 | C-LOGIN-FAIL | Login `user@cosme-shop.com` / `wrong` | 401, error message | ☐ |
| 2.1.6 | C-PROFILE-GUARD | Visit `/profile` while logged out | Redirect to `/login` | ☐ |
| 2.1.7 | C-LOGOUT | Click logout | Token cleared, redirect home | ☐ |
| 2.1.8 | C-ME | After login, `GET /api/auth/me` | Returns user info | ☐ |

### 2.2 Profile

| # | Test ID | Action | Expected Result | Pass |
|---|---|---|---|---|
| 2.2.1 | C-PROFILE-VIEW | Visit `/profile` | Form populated with user data | ☐ |
| 2.2.2 | C-PROFILE-UPDATE | Update full_name, phone, address | 200, new values shown | ☐ |
| 2.2.3 | C-CHANGE-PW | Change password from `user123` → `newpass123` | 200, login with new pw works | ☐ |
| 2.2.4 | C-CHANGE-PW-WRONG | Change password with wrong old pw | 400, error | ☐ |

### 2.3 Wishlist

| # | Test ID | Action | Expected Result | Pass |
|---|---|---|---|---|
| 2.3.1 | C-WISH-ADD | On product detail, click heart icon | Product added, toast confirm | ☐ |
| 2.3.2 | C-WISH-LIST | Visit `/wishlist` | List shows added products with image, name, price | ☐ |
| 2.3.3 | C-WISH-DUP | Try add same product again | 400, "Sản phẩm đã có trong wishlist" | ☐ |
| 2.3.4 | C-WISH-REMOVE | Click remove on wishlist item | Item removed from list | ☐ |

### 2.4 Cart & Checkout

| # | Test ID | Action | Expected Result | Pass |
|---|---|---|---|---|
| 2.4.1 | C-CART-ADD | Add product to cart from detail page | Cart icon shows count | ☐ |
| 2.4.2 | C-CART-VIEW | Visit `/cart` | List cart items with qty controls | ☐ |
| 2.4.3 | C-CART-QTY | Increase qty to 5 | Total updates | ☐ |
| 2.4.4 | C-CART-REMOVE | Remove item | Cart updates, count decrements | ☐ |
| 2.4.5 | C-CHECKOUT | Click "Thanh toán" from cart | Redirect `/checkout` with items | ☐ |
| 2.4.6 | C-CHECKOUT-COD | Fill shipping, choose COD, submit | Order created 201, redirect order detail | ☐ |
| 2.4.7 | C-ORDERS-LIST | Visit `/orders` | List user's orders | ☐ |
| 2.4.8 | C-ORDER-DETAIL | Click on an order | Show status, items, total, shipping | ☐ |
| 2.4.9 | C-ORDER-CANCEL | Cancel pending order | Status → "cancelled" | ☐ |

---

## 3. Admin Persona — 16 cases

### 3.1 Auth & Guard

| # | Test ID | Action | Expected Result | Pass |
|---|---|---|---|---|
| 3.1.1 | A-LOGIN | Login `admin@cosme-shop.com` / `admin123` | 200, redirect `/admin/dashboard` | ☐ |
| 3.1.2 | A-USER-BLOCK | Customer tries `/admin/dashboard` | Redirect to `/` or 403 | ☐ |
| 3.1.3 | A-LOGOUT | Click logout | Token cleared, redirect home | ☐ |

### 3.2 Dashboard

| # | Test ID | Action | Expected Result | Pass |
|---|---|---|---|---|
| 3.2.1 | A-DASH-VIEW | Visit `/admin/dashboard` | Stats: total orders, revenue, product count, user count | ☐ |
| 3.2.2 | A-DASH-RECENT | Scroll to recent orders | Table with 5-10 recent orders | ☐ |

### 3.3 Products CRUD

| # | Test ID | Action | Expected Result | Pass |
|---|---|---|---|---|
| 3.3.1 | A-PROD-LIST | Visit `/admin/products` | Table all 20 products with edit/delete | ☐ |
| 3.3.2 | A-PROD-CREATE | Click "Thêm sản phẩm", fill form, submit | 201, new product in list | ☐ |
| 3.3.3 | A-PROD-EDIT | Edit existing product, change price | 200, new price in list | ☐ |
| 3.3.4 | A-PROD-SOFT-DEL | Click delete on product | is_active=false, hidden from public | ☐ |
| 3.3.5 | A-PROD-NULLABLE | Create product without sale_price | 201, sale_price=null | ☐ |

### 3.4 Categories

| # | Test ID | Action | Expected Result | Pass |
|---|---|---|---|---|
| 3.4.1 | A-CAT-LIST | Visit `/admin/categories` | Table 8 categories | ☐ |
| 3.4.2 | A-CAT-CREATE | Create category "UAT Test" with unique slug | 201, in list | ☐ |
| 3.4.3 | A-CAT-EDIT | Edit category name | 200, new name shown | ☐ |
| 3.4.4 | A-CAT-DELETE | Delete category with no products | 204, removed from list | ☐ |

### 3.5 Orders Management

| # | Test ID | Action | Expected Result | Pass |
|---|---|---|---|---|
| 3.5.1 | A-ORD-LIST | Visit `/admin/orders` | Table all orders from all users | ☐ |
| 3.5.2 | A-ORD-DETAIL | Click on order | Full order info, items, customer | ☐ |
| 3.5.3 | A-ORD-STATUS | Update order status pending → confirmed | 200, status updated | ☐ |
| 3.5.4 | A-ORD-NOTE | Add status history note | 200, note in timeline | ☐ |

### 3.6 Users (optional)

| # | Test ID | Action | Expected Result | Pass |
|---|---|---|---|---|
| 3.6.1 | A-USER-LIST | Visit `/admin/users` | Table all users | ☐ |
| 3.6.2 | A-USER-DEACTIVATE | Toggle active on a test user | is_active=false, user can't login | ☐ |

---

## 4. Cross-cutting — 8 cases

| # | Test ID | Action | Expected Result | Pass |
|---|---|---|---|---|
| 4.1 | X-SEC-ISOLATION | User A login, GET `/api/orders` — verify only own orders | No orders from user B visible | ☐ |
| 4.2 | X-VALIDATION | POST `/api/auth/register` missing email field | 400, validation error | ☐ |
| 4.3 | X-PAGINATION | GET `/api/products?page=2&size=5` | 5 different products, total=20 | ☐ |
| 4.4 | X-FILTER-COMBO | GET `/api/products?skin_types=oily,combination&min_price=100000&max_price=300000` | Filtered + counted | ☐ |
| 4.5 | X-CORS | Frontend at :5173 calls backend at :8000 | CORS allows, no preflight error | ☐ |
| 4.6 | X-AI-FALLBACK | POST `/api/ai/routine` with budget 10M | 200 with steps OR 503 if AI offline | ☐ |
| 4.7 | X-PERF-LIST | GET `/api/products?size=20` response time | < 500ms | ☐ |
| 4.8 | X-LAZY-IMG | Visit product list, scroll | Images lazy load, no 404s | ☐ |

---

## 5. Bug Reporting Template

When you find a bug, file it with:

```markdown
**Test ID**: [from above table]
**Severity**: Critical / High / Medium / Low
**Steps to reproduce**:
1. ...
2. ...
3. ...
**Expected**: ...
**Actual**: ...
**Screenshot**: [attach]
**Browser**: Chrome / Firefox / Safari + version
**Console errors**: [paste]
**Network**: [relevant request/response]
```

## 6. Sign-off

| Role | Name | Date | Signature |
|---|---|---|---|
| Tester | | | |
| Dev Lead | | | |
| PM | | | |

---

## Appendix A: API Endpoint Coverage

| Endpoint | Method | Auth | Tested in |
|---|---|---|---|
| `/api/auth/register` | POST | - | C-REG-* |
| `/api/auth/login` | POST | - | C-LOGIN-* / A-LOGIN |
| `/api/auth/me` | GET | User | C-ME |
| `/api/auth/change-password` | POST | User | C-CHANGE-PW-* |
| `/api/categories` | GET | - | G-CAT-* |
| `/api/categories/{id}` | GET | - | G-CAT-* |
| `/api/categories` | POST | Admin | A-CAT-* |
| `/api/categories/{id}` | PATCH | Admin | A-CAT-* |
| `/api/categories/{id}` | DELETE | Admin | A-CAT-* |
| `/api/brands` | GET | - | G-LIST |
| `/api/brands/{id}` | GET | - | G-LIST |
| `/api/products` | GET | - | G-LIST, G-FILTER-* |
| `/api/products/{id}` | GET | - | G-DETAIL |
| `/api/products/best-sellers` | GET | - | G-BEST |
| `/api/products/{id}/similar` | GET | - | G-SIMILAR |
| `/api/products` | POST | Admin | A-PROD-CREATE |
| `/api/products/{id}` | PATCH | Admin | A-PROD-EDIT |
| `/api/products/{id}` | DELETE | Admin | A-PROD-SOFT-DEL |
| `/api/wishlist` | GET | User | C-WISH-LIST |
| `/api/wishlist/{id}` | POST | User | C-WISH-ADD |
| `/api/wishlist/{id}` | DELETE | User | C-WISH-REMOVE |
| `/api/orders` | GET | User | C-ORDERS-LIST |
| `/api/orders` | POST | User | C-CHECKOUT-COD |
| `/api/orders/{id}` | GET | User/Admin | C-ORDER-DETAIL |
| `/api/orders/{id}/cancel` | POST | User | C-ORDER-CANCEL |
| `/api/admin/orders` | GET | Admin | A-ORD-LIST |
| `/api/admin/orders/{id}/status` | PATCH | Admin | A-ORD-STATUS |
| `/api/admin/users` | GET | Admin | A-USER-LIST |
| `/api/admin/users/{id}/toggle-active` | PATCH | Admin | A-USER-DEACTIVATE |
| `/api/ai/routine` | POST | - | G-QUIZ |
| `/api/upload` | POST | Admin | (manual image upload) |
| `/api/payment/sepay-webhook` | POST | - | (SePay integration) |

## Appendix B: Known Limitations (post-Phase 03)

- AI service URL points to internal cluster (`ai-service:8000`), returns 503 in dev unless AI pod running
- `npm run build` was last verified in Phase 02 (24 errors fixed). Re-verify after seed/image_url changes
- Email confirm flow NOT implemented — register = auto-login
- Wishlist not auto-cleared when product soft-deleted (consider Phase 05)

## Appendix C: How to Reset Environment

```bash
# Backend
cd backend
.venv/bin/python -m app.scripts.seed

# Frontend
cd frontend
npm run dev  # http://localhost:5173

# Reset DB (if needed)
.venv/bin/python -c "
import asyncio
from sqlalchemy import delete
from app.db.session import AsyncSessionLocal
from app.model.user import User
from app.model.order import Order
from app.model.order_item import OrderItem
from app.model.wishlist import Wishlist
async def clear():
    async with AsyncSessionLocal() as db:
        for M in [OrderItem, Order, Wishlist, User]:
            await db.execute(delete(M))
        await db.commit()
asyncio.run(clear())
"
```
