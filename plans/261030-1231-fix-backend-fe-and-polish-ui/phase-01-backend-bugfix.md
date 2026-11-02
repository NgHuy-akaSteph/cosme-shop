# Phase 01 — Backend bugfix (độc lập, không đổi API shape)

Context links: `backend/app/api/users.py`, `backend/app/service/user_service.py`,
`backend/app/service/product_service.py`, `backend/app/service/order_service.py`,
`backend/app/api/payment.py`.

Priority: P0 · Status: ✅ Hoàn thành (2026-10-31)

## Yêu cầu

R1. `/api/admin/users` trả `total` đúng tổng số user trong DB.
R2. `/api/payment/status/{order_id}` yêu cầu đăng nhập, chỉ chủ đơn hoặc admin xem được.
R3. Filter `skin_types` / `concerns` dùng OR (đúng `02-business-requirement.md` §3.2).
R4. `PATCH /api/products/{id}` cho phép gán `null` cho `sale_price`, `description`, `skin_types`, `concerns`, `key_ingredients`, `free_from`, `variants`.
R5. `sold_count` tăng theo số lượng bán khi đơn chuyển `delivered`.
R6. Webhook SePay không đánh dấu paid cho đơn đã `cancelled`.
R7. Dọn import trùng/lặp trong `order_service.py`.

## R1 — Đếm user đúng

`app/service/user_service.py` thêm hàm đếm:

```python
async def count_users(db: AsyncSession) -> int:
    """Dem tong so user."""
    result = await db.execute(select(func.count(User.id)))
    return result.scalar_one()
```

Cần thêm `func` vào import: `from sqlalchemy import select, func`.

Trong `app/api/users.py`:

```python
from app.service.user_service import get_all_users, toggle_user_active, get_user_by_id, count_users
...
total = await count_users(db)
return UserListResponse(data=user_list, total=total, page=page, size=size)
```

Lưu ý: `get_all_users` chỉ nhận `skip`/`limit`, không lọc thêm. Không cần đổi.

## R2 — Bảo vệ endpoint payment status

`app/api/payment.py`:

```python
from app.api.deps import get_current_user

@router.get("/status/{order_id}", response_model=dict)
async def get_payment_status(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.model.user import User

    order = await order_service.get_order_by_id(db, order_id)
    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": "Không tìm thấy đơn hàng", "code": "NOT_FOUND"},
        )
    if order.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"message": "Không có quyền xem đơn hàng này", "code": "FORBIDDEN"},
        )
    return {
        "data": {
            "order_code": order.order_code,
            "payment_status": order.payment_status,
            "paid_at": order.paid_at,
        },
        "message": "OK",
    }
```

Xoá import `from app.api.orders import _order_to_dict` (đang import thừa, tạo phụ thuộc vòng).

## R3 — Filter OR cho skin_types / concerns

Trong `app/service/product_service.py`, `get_products`, thay hai vòng lặp `for skin_type in skin_types:` và `for concern in concerns:` bằng:

```python
    # Filter by skin types (JSON contains any - OR semantics)
    if skin_types:
        cond = or_(*[Product.skin_types.contains([st]) for st in skin_types])
        query = query.where(cond)
        count_query = count_query.where(cond)

    # Filter by concerns (JSON contains any - OR semantics)
    if concerns:
        cond = or_(*[Product.concerns.contains([c]) for c in concerns])
        query = query.where(cond)
        count_query = count_query.where(cond)
```

`or_` đã được import sẵn trong file. Kiểm tra lại: file có `from sqlalchemy import select, func, or_, and_` → OK.

Lưu ý: `Product.skin_types` có thể NULL. `contains` trên NULL cho NULL nên điều kiện loại đúng NULL row, không lỗi.

## R4 — Cho phép gán null khi update product

Trong `app/service/product_service.py`, `update_product`, thay vòng lặp hiện tại:

```python
# Fields cho phep gia tri None (xoa du lieu)
NULLABLE_FIELDS = {
    "description", "sale_price", "skin_types", "concerns",
    "key_ingredients", "free_from", "variants",
}

for key, value in kwargs.items():
    if not hasattr(product, key):
        continue
    if value is None and key not in NULLABLE_FIELDS:
        continue
    setattr(product, key, value)
```

Kiểm tra schema `ProductUpdate` dùng `model_dump(exclude_unset=True)` ở `api/products.py` → field không được gửi sẽ không có trong kwargs. Nhưng field được gửi `null` sẽ có mặt với value `None` → xử lý trên giữ nguyên `None`.

Kiểm tra thêm `api/products.py` update: `update_data = data.model_dump(exclude_unset=True)` rồi `product_service.update_product(db, product_id, **update_data)`. Nếu FE gửi `sale_price: null`, Pydantic vẫn set → có trong exclude_unset → OK.

## R5 — Tăng sold_count khi delivered

Trong `app/service/order_service.py`, `update_order_status`, ngay sau block COD auto-paid:

```python
    # Tang sold_count khi don giao thanh cong
    if new_status == "delivered":
        for item in order.items:
            await db.execute(
                update(Product)
                .where(Product.id == item.product_id)
                .values(sold_count=Product.sold_count + item.qty)
            )
```

Cần thêm `update` vào import: `from sqlalchemy import select, func, and_, update`.

Kiểm tra thứ tự: `order.items` đã được load sẵn do `get_order_by_id` dùng `selectinload(Order.items)`.

## R6 — Webhook bỏ qua đơn đã hủy

Trong `app/api/payment.py`, ngay sau khi lấy được `order` (trước check amount):

```python
        # Don da huy: khong danh dau paid, can hoan tien thu cong
        if order.status == "cancelled":
            logger.warning(
                "SePay: order %s da huy nhung van nhan tien. Can xu ly hoan tien thu cong.",
                order_code,
            )
            return {"success": True}
```

## R7 — Dọn import

`app/service/order_service.py` hiện có `from app.model.product import Product` ở dòng 15 và lặp lại ở dòng 29, cùng `from app.model.user import User` không dùng. Xoá dòng 29-30 (giữ 1 import Product, bỏ import User).

## Files cần sửa

- Sửa: `backend/app/service/user_service.py`
- Sửa: `backend/app/api/users.py`
- Sửa: `backend/app/api/payment.py`
- Sửa: `backend/app/service/product_service.py`
- Sửa: `backend/app/service/order_service.py`
- Không tạo file mới. Không cần migration DB.

## Todo

- [x] R1 count_users
- [x] R2 payment status auth
- [x] R3 filter OR
- [x] R4 update null
- [x] R5 sold_count
- [x] R6 webhook cancelled
- [x] R7 dọn import
- [x] `cd backend && .venv/bin/python -c "import app.main"` (compile check)

## Success criteria

- `GET /api/admin/users?size=1` → `total` = số user thật (không phải 1).
- `GET /api/products?skin_types=oily,combination` → trả về sản phẩm có **một trong hai** loại da.
- Admin gửi `PATCH /api/products/{id}` với `sale_price: null` → sau đó GET thì `sale_price` null.
- `GET /api/payment/status/{id}` không token → 401; token của user khác → 403.
- Đơn COD chuyển `delivered` → `sold_count` tăng đúng số lượng.

## Risk

Sửa R3 đổi hành vi filter → kết quả danh sách sản phẩm nhiều hơn trước. Đây là đúng spec, nhưng cần ghi chú trong changelog.
