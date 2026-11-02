# Phase 01: Fix Backend Blockers (bcrypt + Model Mapper)

## Context Links

- [plan.md](plan.md) — Overview
- [docs/03-tech-stack.md](../../docs/03-tech-stack.md) — Backend dependencies
- [backend/app/core/security.py](../../backend/app/core/security.py) — Hash/verify logic
- [backend/app/db/session.py](../../backend/app/db/session.py) — DB engine + session
- [backend/app/service/product_service.py](../../backend/app/service/product_service.py) — Uses Product.images_rel
- [backend/app/model/product.py](../../backend/app/model/product.py) — Has `images_rel` relationship
- [backend/app/model/product_image.py](../../backend/app/model/product_image.py) — ProductImage model
- [backend/alembic/env.py](../../backend/alembic/env.py) — Already imports all models (good reference)

## Overview

- **Priority**: P0 (blocker)
- **Status**: Pending
- **Brief**: Fix 2 blockers: (1) bcrypt/passlib compatibility, (2) SQLAlchemy mapper init.

## Key Insights

### Blocker 1: bcrypt 5.x × passlib 1.7.4

- `bcrypt==5.0.0` đã xoá `__about__.__version__` attribute
- `passlib==1.7.4` đọc `bcrypt.__about__.__version__` ở dòng 620 của `bcrypt.py`
- Handler init broken → `CryptContext.hash()` raise ValueError với mọi password

**Verify đã làm**:
```python
from app.core.security import hash_password
hash_password("test123")  # → ValueError("password cannot be longer than 72 bytes...")
```

### Blocker 2: Product ↔ ProductImage mapper

- `Product.images_rel` relationship dùng string forward ref: `relationship("ProductImage", ..., order_by="ProductImage.position")`
- Khi `selectinload(Product.images_rel)` execute, SQLAlchemy phải resolve `ProductImage.position` để build ORDER BY
- `product_service.py` chỉ import `Product, Category, Brand` — không import `ProductImage`
- `product_image_service.py` import `ProductImage` nhưng chỉ được load khi gọi API upload, không khi query products

**Verify đã làm**:
```python
# Fail ngay khi query Product đầu tiên:
select(Product).options(selectinload(Product.images_rel)).limit(1)
# → InvalidRequestError: expression 'ProductImage.position' failed to locate a name
```

## Requirements

### Functional
- `hash_password(pwd)` return bcrypt hash hợp lệ cho pwd 1-72 bytes
- `verify_password(plain, hash)` return True/False đúng
- `POST /api/auth/register` trả 201 với user mới
- `POST /api/auth/login` trả 200 với user + token
- `select(Product).options(selectinload(Product.images_rel))` chạy không raise

### Non-Functional
- Không tăng thời gian hash đáng kể
- Vẫn dùng bcrypt (cost 12) cho an toàn

## Architecture

### Decision: bcrypt 4.0.1 thay vì 5.0.0

| Option | Pros | Cons |
|---|---|---|
| Pin `bcrypt==4.0.1` | Drop-in, passlib 1.7.4 work; minimal change | bcrypt 4 hơi cũ |
| Bỏ passlib, dùng `bcrypt` trực tiếp | Latest bcrypt | Phải viết lại `security.py` |
| Đổi sang `argon2-cffi` | Modern, không có compat issue | Phải đổi hash format → user cũ không login được |

**Chọn Option 1** (pin bcrypt==4.0.1) vì:
- Drop-in, ít thay đổi
- User cũ trong DB vẫn verify được (bcrypt hash format backward compat)
- passlib 1.7.4 đã stable từ lâu, không nâng cấp sớm

### Decision: Import tất cả models trong `db/session.py`

- Đặt sau khi tạo `engine`, trước khi trả `AsyncSessionLocal`
- Đảm bảo mọi model class được register vào `Base.metadata`
- Khi bất kỳ relationship string forward ref nào resolve, class đã available

## Related Code Files

### Modify
- [backend/requirements.txt](../../backend/requirements.txt) — Pin `bcrypt==4.0.1`
- [backend/app/db/session.py](../../backend/app/db/session.py) — Add model imports
- (optional) [backend/app/service/product_service.py](../../backend/app/service/product_service.py) — Could import ProductImage local, nhưng session.py import là cleaner

### Read for context
- [backend/app/core/security.py](../../backend/app/core/security.py) — Xem `hash_password`/`verify_password` implementation
- [backend/app/model/__init__.py](../../backend/app/model/__init__.py) — Check nếu đã có import all

### No delete

## Implementation Steps

### Step 1.1: Pin bcrypt==4.0.1

```bash
# Trong backend/.venv đã có bcrypt 5.0.0
/home/huyquang/Workspace/School/cosme-shop/backend/.venv/bin/pip install 'bcrypt==4.0.1'
```

Update `backend/requirements.txt`:
```diff
-bcrypt==5.0.0
+bcrypt==4.0.1
```

### Step 1.2: Verify hash_password hoạt động

```bash
cd /home/huyquang/Workspace/School/cosme-shop/backend
.venv/bin/python -c "
from app.core.security import hash_password, verify_password
h = hash_password('test123')
print('Hash:', h[:30])
print('Verify:', verify_password('test123', h))
"
```

Expected: không có traceback, print hash + True.

### Step 1.3: Add model imports trong `db/session.py`

Append sau khi tạo engine, trước `get_db`:

```python
# Import all models để SQLAlchemy register đầy đủ mapper.
# Cần thiết để resolve forward string refs (vd: Product.images_rel -> ProductImage.position)
from app.model.user import User  # noqa: F401, E402
from app.model.category import Category  # noqa: F401, E402
from app.model.brand import Brand  # noqa: F401, E402
from app.model.product import Product  # noqa: F401, E402
from app.model.product_image import ProductImage  # noqa: F401, E402
from app.model.order import Order  # noqa: F401, E402
from app.model.order_item import OrderItem  # noqa: F401, E402
from app.model.order_status_history import OrderStatusHistory  # noqa: F401, E402
from app.model.wishlist import Wishlist  # noqa: F401, E402
```

### Step 1.4: Verify mapper init

```bash
.venv/bin/python -c "
import asyncio, warnings
warnings.filterwarnings('ignore')
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.db.session import AsyncSessionLocal
from app.model.product import Product

async def test():
    async with AsyncSessionLocal() as db:
        r = await db.execute(select(func.count(Product.id)))
        print(f'count(Product): {r.scalar()}')
        r = await db.execute(
            select(Product).options(
                selectinload(Product.category),
                selectinload(Product.brand),
                selectinload(Product.images_rel),
            ).limit(1)
        )
        rows = list(r.scalars().all())
        print(f'Select eager: {len(rows)} rows')

asyncio.run(test())
"
```

Expected: cả 2 query chạy OK.

### Step 1.5: Live API smoke test

```bash
.venv/bin/python << 'EOF'
import asyncio, warnings, time
warnings.filterwarnings('ignore')
from httpx import AsyncClient, ASGITransport
from app.main import app

async def test():
    email = f'phase1{int(time.time())}@uat.com'
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as c:
        # Register
        r = await c.post('/api/auth/register', json={'email': email, 'password': 'test123', 'full_name': 'P1'})
        print(f'Register: {r.status_code}')
        assert r.status_code == 201, r.text
        token = r.json()['data']['access_token']
        # Login back
        r = await c.post('/api/auth/login', json={'email': email, 'password': 'test123'})
        print(f'Login: {r.status_code}')
        assert r.status_code == 200, r.text
        # /me
        r = await c.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'})
        print(f'Me: {r.status_code}')
        assert r.status_code == 200, r.text
        # /api/products
        r = await c.get('/api/products?size=5')
        print(f'Products: {r.status_code} count={r.json().get(\"total\")}')
        assert r.status_code == 200

asyncio.run(test())
EOF
```

Expected: tất cả 4 calls return status đúng.

## Todo List

- [ ] Step 1.1: Pin `bcrypt==4.0.1` trong `.venv` + update `requirements.txt`
- [ ] Step 1.2: Verify `hash_password('test123')` không raise
- [ ] Step 1.3: Add model imports vào `backend/app/db/session.py`
- [ ] Step 1.4: Verify `selectinload(Product.images_rel)` chạy
- [ ] Step 1.5: Live API smoke test (register/login/me/products)

## Success Criteria

- `hash_password` + `verify_password` round-trip OK
- Tất cả 4 API smoke test trên pass
- Không có regression ở các endpoint khác

## Risk Assessment

### Risk 1: bcrypt downgrade break existing hashes

- Mitigation: bcrypt 4.x và 5.x đều dùng cùng hash format `$2b$...` → backward compatible. User cũ trong DB vẫn verify được.
- Verify: login với 1 user cũ (vd: `uat@cosme.com`) sau fix để confirm.

### Risk 2: Import order gây circular

- Mitigation: chỉ import trong `db/session.py` (sau `from app.core.config import settings`), không import trong model file. Model files không depend lẫn nhau.
- Verify: import order test ở Step 1.4.

### Risk 3: `pip install bcrypt==4.0.1` fail

- Mitigation: nếu conflict, uninstall `bcrypt==5.0.0` trước: `pip uninstall bcrypt -y && pip install bcrypt==4.0.1`

## Security Considerations

- KHÔNG touch `JWT_SECRET_KEY` hoặc bất kỳ secret nào
- KHÔNG log password hash hoặc plain password
- bcrypt cost 12 vẫn giữ nguyên (qua passlib default)

## Next Steps

Sau khi Phase 01 xong → chạy [Phase 02: Fix Frontend Build](phase-02-fix-frontend-build.md)