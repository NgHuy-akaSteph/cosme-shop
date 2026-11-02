# Phase 03: Seed Database & Smoke Test API

## Context Links

- [plan.md](plan.md) — Overview
- [phase-01-fix-backend-blockers.md](phase-01-fix-backend-blockers.md) — Prerequisite
- [phase-02-fix-frontend-build.md](phase-02-fix-frontend-build.md) — Prerequisite
- [backend/app/scripts/seed.py](../../backend/app/scripts/seed.py) — Seed script

## Overview

- **Priority**: P1 (sau khi 2 blocker fix xong)
- **Status**: Pending
- **Brief**: Verify seed chạy thành công, có data để test UI, và tất cả endpoint round-trip OK.

## Key Insights

### Hiện trạng DB

- DB Neon đã có 1 số user test cũ (`uat@cosme.com`, `fresh@uat.com`, `user1791841828@uat.com`)
- Không chắc có categories/brands/products
- **Cần reset sạch trước khi seed để có môi trường deterministic cho UAT**

### Sau seed cần có:

- 1 admin user (vd: `admin@cosme.com` / `admin123`)
- 1 user mẫu (vd: `user@cosme.com` / `user123`)
- 5-10 categories
- 5 brands
- 20-30 products (mix có/không variants, có/không sale_price)
- Đủ JSON fields (`skin_types`, `concerns`, `key_ingredients`, `free_from`) để test Routine Builder

## Requirements

### Functional
- Seed script chạy thành công không raise
- Tất cả public API trả data hợp lệ sau seed
- Admin auth + CRUD product thành công

### Non-Functional
- Seed idempotent hoặc skip nếu data tồn tại (tránh duplicate)
- Không bị SQLAlchemy lỗi relationship

## Related Code Files

### Modify
- [backend/app/scripts/seed.py](../../backend/app/scripts/seed.py) — Nếu cần thêm model import

### Read for context
- [docs/04-database.md](../../docs/04-database.md) — Section 11: Seed data specs
- [docs/02-business-requirement.md](../../docs/02-business-requirement.md) — Section 7: Demo scenarios

### No delete

## Implementation Steps

### Step 3.1: Verify seed script imports đúng models

```bash
cd /home/huyquang/Workspace/School/cosme-shop/backend
.venv/bin/python -c "from app.scripts.seed import seed; print('seed import OK')"
```

Nếu lỗi, cần thêm import:
```python
from app.model.product_image import ProductImage  # noqa
```

### Step 3.2: Inspect seed.py hiện tại

```bash
cat app/scripts/seed.py
```

Check:
- Có skip nếu data exists?
- Có hard-code password (admin123, user123) theo convention docs?

### Step 3.3: Clear existing test users (optional)

Nếu muốn môi trường clean:

```bash
# Dùng psql hoặc qua Python:
.venv/bin/python << 'EOF'
import asyncio
from sqlalchemy import delete
from app.db.session import AsyncSessionLocal
from app.model.user import User

async def clear():
    async with AsyncSessionLocal() as db:
        await db.execute(delete(User).where(User.email.like('%uat.com')))
        await db.commit()
        print('Cleared test users')

asyncio.run(clear())
EOF
```

Hoặc dùng Adminer (`http://localhost:8080`) để truncate table.

**Cảnh báo**: xoá user có thể ảnh hưởng order/wishlist (FK CASCADE). OK cho dev.

### Step 3.4: Chạy seed

```bash
.venv/bin/python -m app.scripts.seed
```

Expected: in ra số records đã insert.

### Step 3.5: Verify data

```bash
.venv/bin/python << 'EOF'
import asyncio
from sqlalchemy import select, func
from app.db.session import AsyncSessionLocal
from app.model.user import User
from app.model.category import Category
from app.model.brand import Brand
from app.model.product import Product

async def check():
    async with AsyncSessionLocal() as db:
        for M, n in [(User, 'users'), (Category, 'categories'), (Brand, 'brands'), (Product, 'products')]:
            r = await db.execute(select(func.count(M.id)))
            print(f'{n}: {r.scalar()}')

asyncio.run(check())
EOF
```

Expected:
- users: ≥ 2 (admin + user)
- categories: ≥ 5
- brands: ≥ 5
- products: ≥ 20

### Step 3.6: Full API smoke test

```bash
.venv/bin/python << 'EOF'
import asyncio, warnings, json
warnings.filterwarnings('ignore')
from httpx import AsyncClient, ASGITransport
from app.main import app

ADMIN_EMAIL = 'admin@cosme.com'  # adjust to seed output
ADMIN_PASS = 'admin123'           # adjust

async def test():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test', timeout=15) as c:
        # 1. Public endpoints
        r = await c.get('/api/products?size=5')
        print(f'GET /api/products: {r.status_code} total={r.json().get("total")}')
        assert r.status_code == 200
        assert r.json()['total'] > 0

        r = await c.get('/api/products/best-sellers?limit=4')
        print(f'GET /api/products/best-sellers: {r.status_code} count={len(r.json()["data"])}')
        assert r.status_code == 200

        r = await c.get('/api/categories')
        print(f'GET /api/categories: {r.status_code} total={r.json().get("total")}')
        assert r.json()['total'] > 0

        r = await c.get('/api/brands')
        print(f'GET /api/brands: {r.status_code} total={r.json().get("total")}')
        assert r.json()['total'] > 0

        # 2. Login admin
        r = await c.post('/api/auth/login', json={'email': ADMIN_EMAIL, 'password': ADMIN_PASS})
        print(f'Admin login: {r.status_code}')
        assert r.status_code == 200, r.text
        token = r.json()['data']['access_token']
        user = r.json()['data']['user']
        assert user['role'] == 'admin'
        auth = {'Authorization': f'Bearer {token}'}

        # 3. Admin: create category
        r = await c.post('/api/categories', json={'name': 'UAT Test', 'slug': f'uat-{int(__import__("time").time())}'}, headers=auth)
        print(f'POST /api/categories (admin): {r.status_code}')
        assert r.status_code in (201, 400), r.text  # 400 if duplicate slug

        # 4. Admin: list all products (no size limit, just verify access)
        r = await c.get('/api/products?size=5', headers=auth)
        print(f'GET /api/products (admin): {r.status_code}')
        assert r.status_code == 200

        # 5. AI routine (public, no auth)
        r = await c.post('/api/ai/routine', json={'quiz': {'skin_type': 'oily', 'concerns': ['acne'], 'budget': 500000, 'age': 25}})
        print(f'POST /api/ai/routine: {r.status_code}')
        # 503 OK nếu AI service không chạy; 200 nếu có data
        assert r.status_code in (200, 503), r.text

asyncio.run(test())
EOF
```

### Step 3.7: User flow smoke test

```bash
.venv/bin/python << 'EOF'
import asyncio, warnings, time
warnings.filterwarnings('ignore')
from httpx import AsyncClient, ASGITransport
from app.main import app

USER_EMAIL = 'user@cosme.com'  # adjust
USER_PASS = 'user123'           # adjust

async def test():
    email = f'smoke{int(time.time())}@cosme.com'
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test', timeout=15) as c:
        # Register
        r = await c.post('/api/auth/register', json={'email': email, 'password': 'smoke123', 'full_name': 'Smoke'})
        assert r.status_code == 201, r.text
        tok = r.json()['data']['access_token']
        auth = {'Authorization': f'Bearer {tok}'}

        # /me
        r = await c.get('/api/auth/me', headers=auth)
        assert r.status_code == 200, r.text

        # Add to wishlist
        r = await c.post('/api/wishlist/1', headers=auth)
        print(f'Add wishlist: {r.status_code}')
        # 400 if product 1 doesn't exist

        # Get wishlist
        r = await c.get('/api/wishlist', headers=auth)
        print(f'Get wishlist: {r.status_code}')

        # Create order (need valid product)
        r = await c.get('/api/products?size=1')
        if r.json()['data']:
            pid = r.json()['data'][0]['id']
            r = await c.post('/api/orders', headers=auth, json={
                'items': [{'product_id': pid, 'qty': 1}],
                'shipping_name': 'Smoke', 'shipping_phone': '0901234567',
                'shipping_address': 'Test', 'payment_method': 'cod'
            })
            print(f'Create order: {r.status_code}')
            assert r.status_code in (201, 400, 404), r.text

asyncio.run(test())
EOF
```

## Todo List

- [ ] Step 3.1: Verify seed import
- [ ] Step 3.2: Inspect seed.py (check convention)
- [ ] Step 3.3: Clear test users (optional)
- [ ] Step 3.4: Run seed
- [ ] Step 3.5: Verify data count
- [ ] Step 3.6: API smoke test (public + admin)
- [ ] Step 3.7: User flow smoke test

## Success Criteria

- Seed chạy thành công, ≥ 20 products, ≥ 5 categories/brands
- Tất cả public endpoint trả 200 với data
- Admin login + create category OK
- User register + create order OK
- Không có SQLAlchemy error

## Risk Assessment

### Risk 1: Seed duplicate error

- Mitigation: xoá data cũ trước, hoặc sửa seed.py để check exists trước khi insert.

### Risk 2: Admin password không match convention

- Mitigation: docs đề xuất `admin@cosme.com` / `admin123` và `user@cosme.com` / `user123`. Nếu seed hard-code khác → đọc seed.py để biết.

### Risk 3: AI service không chạy

- Mitigation: AI endpoint sẽ trả 503 với code AI_SERVICE_ERROR (đã handle trong code). UAT vẫn chạy được phần khác.

## Security Considerations

- KHÔNG commit password admin/user vào git
- Seed dùng cho dev/staging, production phải đổi
- Nếu DB thật đang có data user thật → KHÔNG chạy clear ở Step 3.3

## Next Steps

Sau khi Phase 03 xong → [Phase 04: UAT Checklist](phase-04-uat-checklist.md)