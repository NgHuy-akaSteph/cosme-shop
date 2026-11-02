# Phase 02 — Backend hardening (DRY, validate, API thống kê cho dashboard)

Context links: `backend/app/api/orders.py`, `backend/app/api/admin.py`,
`backend/app/service/order_service.py`, `backend/app/schemas/order.py`,
`backend/app/main.py`.

Priority: P0 (stats) / P1 (DRY, validate) · Status: ✅ Hoàn thành (2026-10-31)

## Yêu cầu

R1. Gộp `_order_to_dict` đang copy-paste giữa `orders.py` và `admin.py` về một chỗ.
R2. Backend validate số điện thoại VN, tên người nhận và địa chỉ (hiện chỉ FE validate).
R3. Thêm `GET /api/admin/stats` cấp số liệu cho dashboard: doanh thu, đơn theo trạng thái, doanh thu 7 ngày, top sản phẩm, sản phẩm sắp hết.

## R1 — Gộp serializer order

Hiện tại `backend/app/api/orders.py` và `backend/app/api/admin.py` có cùng một hàm ~60 dòng.

Đặt hàm vào `backend/app/service/order_service.py` (dưới cùng file) vì cả hai API module đã import `order_service`:

```python
def order_to_dict(order: Order) -> dict[str, Any]:
    """Chuyen order model sang dict (dung chung cho user API va admin API)."""
    return {
        "id": order.id,
        "user_id": order.user_id,
        "order_code": order.order_code,
        "status": order.status,
        "subtotal": str(order.subtotal),
        "shipping_fee": str(order.shipping_fee),
        "discount": str(order.discount),
        "total": str(order.total),
        "payment_method": order.payment_method,
        "payment_status": order.payment_status,
        "paid_at": order.paid_at,
        "transaction_id": order.transaction_id,
        "shipping_name": order.shipping_name,
        "shipping_phone": order.shipping_phone,
        "shipping_address": order.shipping_address,
        "tracking_code": order.tracking_code,
        "carrier": order.carrier,
        "note": order.note,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "product_price": str(item.product_price),
                "product_image": item.product_image,
                "variant_info": item.variant_info,
                "qty": item.qty,
                "subtotal": str(item.subtotal),
            }
            for item in order.items
        ],
        "status_history": [
            {
                "id": h.id,
                "status": h.status,
                "note": h.note,
                "created_by": h.created_by,
                "created_at": h.created_at,
            }
            for h in sorted(order.status_history, key=lambda x: x.created_at, reverse=True)
        ],
    }
```

Sau đó trong `orders.py` và `admin.py`:
- Xoá hàm `_order_to_dict` cục bộ.
- Thay mọi lời gọi `_order_to_dict(x)` bằng `order_service.order_to_dict(x)`.

Kiểm tra: `payment.py` đang import `from app.api.orders import _order_to_dict` — xoá dòng import này (Phase 01 đã xử lý, giữ nhất quán).

## R2 — Validate đầu vào checkout

`backend/app/schemas/order.py`, class `OrderBase`:

```python
class OrderBase(BaseModel):
    """Base schema cho order"""
    items: list[OrderItemBase]
    shipping_name: str = Field(..., min_length=2, max_length=255)
    shipping_phone: str = Field(..., pattern=r"^0\d{9,10}$")
    shipping_address: str = Field(..., min_length=5)
    payment_method: str = Field(..., pattern="^(cod|sepay)$")
    note: str | None = None
```

`OrderItemBase.qty` đã có `gt=0`. Nên thêm giới hạn trên để tránh đặt 10000 sản phẩm trong 1 lần:

```python
class OrderItemBase(BaseModel):
    product_id: int
    variant_id: str | None = None
    qty: int = Field(..., gt=0, le=99)
```

Lưu ý: `main.py` đã có handler `RequestValidationError` trả 400 với `code="VALIDATION_ERROR"`. FE đọc `message` sẽ hiện "Dữ liệu không hợp lệ" (generic). Nếu muốn chi tiết hơn, sửa handler trả `detail` là message đầu tiên của lỗi:

```python
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    errors = exc.errors()
    first = errors[0] if errors else {}
    msg = first.get("msg", "Dữ liệu không hợp lệ")
    return JSONResponse(
        status_code=400,
        content={
            "detail": f"Dữ liệu không hợp lệ: {msg}",
            "code": "VALIDATION_ERROR",
            "errors": errors,
        },
    )
```

Điều này giúp user thấy "Số điện thoại không hợp lệ" thay vì thông báo chung. Phải chắc chắn FE dùng `getErrorMessage` (Phase 03 xử lý).

## R3 — API thống kê cho admin dashboard

Tạo `backend/app/service/stats_service.py`:

```python
"""Stats service - so lieu thong ke cho admin dashboard"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.order import Order
from app.model.order_item import OrderItem
from app.model.product import Product
from app.model.user import User


async def get_dashboard_stats(db: AsyncSession, days: int = 7) -> dict:
    """Lay tong hop so lieu: doanh thu, don hang, san pham, khach hang."""
    # Tong don hang
    total_orders = (await db.execute(select(func.count(Order.id)))).scalar_one()

    # Doanh thu: chi tinh don da thanh toan (cod+delivered hoac sepay+paid)
    revenue = (
        await db.execute(
            select(func.coalesce(func.sum(Order.total), 0)).where(
                Order.payment_status == "paid"
            )
        )
    ).scalar_one()

    # Doanh thu chua thanh toan (COD chua giao)
    pending_revenue = (
        await db.execute(
            select(func.coalesce(func.sum(Order.total), 0)).where(
                Order.payment_status == "unpaid", Order.status != "cancelled"
            )
        )
    ).scalar_one()

    # Don theo trang thai
    status_rows = await db.execute(
        select(Order.status, func.count(Order.id))
        .group_by(Order.status)
    )
    orders_by_status = {status: count for status, count in status_rows.all()}

    # Doanh thu 7 ngay gan nhat (theo ngay tao don, chi don da thanh toan)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    daily_rows = await db.execute(
        select(
            func.date(Order.created_at).label("day"),
            func.coalesce(func.sum(Order.total), 0).label("revenue"),
            func.count(Order.id).label("orders"),
        )
        .where(Order.created_at >= since, Order.payment_status == "paid")
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
    )
    revenue_by_day = [
        {"day": str(row.day), "revenue": str(row.revenue), "orders": row.orders}
        for row in daily_rows.all()
    ]

    # Top san pham ban chay (theo so luong ban trong don da giao)
    top_rows = await db.execute(
        select(
            OrderItem.product_name,
            func.sum(OrderItem.qty).label("qty"),
            func.sum(OrderItem.subtotal).label("revenue"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.status == "delivered")
        .group_by(OrderItem.product_name)
        .order_by(func.sum(OrderItem.qty).desc())
        .limit(5)
    )
    top_products = [
        {"name": r.product_name, "qty": r.qty, "revenue": str(r.revenue)}
        for r in top_rows.all()
    ]

    # San pham sap het hang
    low_stock_rows = await db.execute(
        select(Product.id, Product.name, Product.stock, Product.sale_price, Product.price)
        .where(Product.is_active == True, Product.stock <= 10)
        .order_by(Product.stock.asc())
        .limit(10)
    )
    low_stock = [
        {
            "id": r.id,
            "name": r.name,
            "stock": r.stock,
            "price": str(r.sale_price or r.price),
        }
        for r in low_stock_rows.all()
    ]

    return {
        "total_orders": total_orders,
        "total_revenue": str(revenue),
        "pending_revenue": str(pending_revenue),
        "total_products": (await db.execute(
            select(func.count(Product.id)).where(Product.is_active == True)
        )).scalar_one(),
        "total_users": (await db.execute(select(func.count(User.id)))).scalar_one(),
        "orders_by_status": orders_by_status,
        "revenue_by_day": revenue_by_day,
        "top_products": top_products,
        "low_stock": low_stock,
    }
```

Tạo `backend/app/api/admin_stats.py`:

```python
"""Admin API - thong ke dashboard"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.model.user import User
from app.service.stats_service import get_dashboard_stats

router = APIRouter(prefix="/api/admin/stats", tags=["admin-stats"])


@router.get("", response_model=dict)
async def dashboard_stats(
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lay tong hop so lieu cho dashboard admin."""
    stats = await get_dashboard_stats(db)
    return {"data": stats, "message": "OK"}
```

Đăng ký router trong `backend/app/main.py`, cạnh các router khác:

```python
    from app.api.admin_stats import router as admin_stats_router
    ...
    app.include_router(admin_stats_router)
```

Ghi chú kỹ thuật:
- `func.date(Order.created_at)` trên Postgres trả `date`. Với `DateTime(timezone=True)` và `datetime.now(timezone.utc)`, so sánh timestamp là an toàn.
- Doanh thu chỉ tính `payment_status == "paid"`. Đơn COD được đánh paid khi `delivered` (đã có ở `update_order_status`).
- Nên bọc `get_dashboard_stats` trong try/except để lỗi 1 phần không làm sập cả dashboard? Không cần — nếu lỗi thì trả 500 là đúng.

## Files cần sửa

- Sửa: `backend/app/service/order_service.py` (thêm `order_to_dict`)
- Sửa: `backend/app/api/orders.py` (dùng serializer chung)
- Sửa: `backend/app/api/admin.py` (dùng serializer chung)
- Sửa: `backend/app/schemas/order.py` (validate)
- Sửa: `backend/app/main.py` (handler message + đăng ký router)
- Tạo: `backend/app/service/stats_service.py`
- Tạo: `backend/app/api/admin_stats.py`
- Không cần migration DB (không đổi schema).

## Todo

- [x] R1 gộp serializer
- [x] R2 validate + handler message
- [x] R3 stats_service + admin_stats + đăng ký router
- [x] `cd backend && .venv/bin/python -c "import app.main"` (compile check)
- [x] Smoke: `curl -H "Authorization: Bearer <admin_token>" http://localhost:8000/api/admin/stats`

## Success criteria

- `GET /api/admin/stats` với token admin trả 200 và có đủ khoá: `total_revenue`, `orders_by_status`, `revenue_by_day`, `top_products`, `low_stock`.
- Token thiếu → 401; token user thường → 403.
- `POST /api/orders` với `shipping_phone = "abc"` → 400 với message nhắc SĐT không hợp lệ.
- `orders.py` và `admin.py` không còn định nghĩa hàm `_order_to_dict`.

## Risk

- `revenue_by_day` có thể rỗng nếu không có đơn paid nào → FE phải xử lý mảng rỗng.
- Thêm endpoint mới → cần cập nhật `docs/03-tech-stack.md` (mục API) và `plans/.../reports/uat-checklist.md` (Appendix A).
