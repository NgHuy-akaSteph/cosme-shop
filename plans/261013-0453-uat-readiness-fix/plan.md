# Plan: UAT Readiness Fix — cosme-shop

## Overview

Sau khi kiểm tra matching FE ↔ BE, phát hiện **2 BE blockers + 24 TS build errors** ngăn hệ thống sẵn sàng UAT. Plan này fix các blocker theo thứ tự ưu tiên để có thể chạy test UAT end-to-end (register → login → CRUD product → cart → checkout → admin tracking).

**Status**: COMPLETE (all 4 phases)
**Date**: 2026-10-13
**Priority**: P0 — Block toàn bộ UAT (RESOLVED)

## Phases

| Phase | Mô tả | Status |
|---|---|---|
| [phase-01-fix-backend-blockers.md](phase-01-fix-backend-blockers.md) | Fix bcrypt + model mapper (blocker auth + DB query) | ✅ Complete |
| [phase-02-fix-frontend-build.md](phase-02-fix-frontend-build.md) | Fix 24 TypeScript errors (build pass) | ✅ Complete |
| [phase-03-seed-and-smoke-test.md](phase-03-seed-and-smoke-test.md) | Seed DB + smoke test API endpoints | ✅ Complete |
| [phase-04-uat-checklist.md](phase-04-uat-checklist.md) | UAT checklist cho 3 personas | ✅ Complete |

## Key Issues Found

### BE Blocker 1 — bcrypt × passlib incompatibility

- `requirements.txt`: `passlib[bcrypt]==1.7.4` + `bcrypt==5.0.0`
- bcrypt 5.x xoá `__about__.__version__` → passlib 1.7.4 handler init broken
- Test thực tế: `hash_password("test123")` raise `ValueError`
- **Ảnh hưởng**: Toàn bộ auth flow fail (register/login/change-password/me)

### BE Blocker 2 — SQLAlchemy mapper can't init Product ↔ ProductImage

- `Product.images_rel` uses string forward ref `"ProductImage"`
- `product_service.py` không import `ProductImage`
- Khi query Product với `selectinload(Product.images_rel)`, mapper crash
- **Ảnh hưởng**: Mọi product/wishlist/order/AI endpoint fail khi DB có data

### FE Build Failures (24 errors)

- `verbatimModuleSyntax` yêu cầu `import type` cho ReactNode
- Antd `Typography.Text` bị destructure nhầm trong `AdminOrders.tsx`
- `Menu items` có `{type: 'divider'}` không match `ItemType[]` types
- `noUnusedLocals` cho nhiều import không dùng
- `Input.TextArea` có prop `prefix` không hợp lệ

## Dependencies

- Python 3.12 + .venv có sẵn ở `backend/.venv/`
- Node 20 + npm có sẵn
- Database: Neon PostgreSQL (đã config trong `backend/.env`)

## Acceptance Criteria

- [x] `python -c "from app.main import app"` không raise
- [x] `hash_password("test123")` return hash thành công
- [x] `register` API trả 201 với user mới
- [x] `select(Product).options(selectinload(Product.images_rel))` chạy không raise
- [x] `npm run build` exit code 0
- [x] `python -m app.scripts.seed` chạy thành công (20 products)
- [x] `GET /api/products` trả data sau khi seed
- [x] `POST /api/auth/register` + `POST /api/auth/login` round-trip OK
- [x] `POST /api/orders` round-trip OK
- [x] FE dev server: `/login`, `/products`, `/cart`, `/checkout` không crash trên browser console

## Additional Deliverables (Post-Plan)

- ✅ JSONB migration: products + order_items (`a8b3c4d5e6f7`)
- ✅ Drop routine columns: usage_time, step (`b9c4d5e6f7a8`)
- ✅ AI/Routine Builder module fully removed (commit `e8399bb`)
- ✅ UAT checklist: `reports/uat-checklist.md` (52 test cases)

## Risks

- **Data hiện tại trong Neon**: Có 1 số user test cũ (`uat@cosme.com`, `fresh@uat.com`). Sau khi fix auth, cần quyết định reset DB hay giữ.
- **bcrypt downgrade**: Khi pin `bcrypt==4.0.1`, cần reinstall và có thể phải restart venv.
- **Import order**: Thêm import model có thể gây circular import nếu không cẩn thận — chỉ import trong `db/session.py` sau engine, không trong model file.

## Security Notes

- `JWT_SECRET_KEY` trong `.env` là placeholder — OK cho dev nhưng KHÔNG commit production.
- `POSTGRES_PASSWORD` đang hard-code trong `.env` — file này không nên commit vào git.
- `CORS_ORIGINS` đang comment out → default chỉ cho `http://localhost:3000`.

## Next Steps

1. ~~Sau khi user OK plan → chạy Phase 01 (BE blockers) theo thứ tự~~ ✅ DONE
2. ~~Chạy smoke test backend sau mỗi fix~~ ✅ DONE
3. ~~Phase 02 (FE build) — fix từng lỗi ưu tiên runtime trước, rồi unused locals~~ ✅ DONE
4. ~~Phase 03 (seed + smoke) — verify tất cả endpoint round-trip~~ ✅ DONE
5. ~~Phase 04 (UAT checklist) — list test case cho 3 personas~~ ✅ DONE

**System is UAT-ready.** Tester team có thể bắt đầu session với checklist tại `reports/uat-checklist.md`.