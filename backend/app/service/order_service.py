"""Order service - business logic"""

import logging
import random
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.model.order import Order
from app.model.order_item import OrderItem
from app.model.order_status_history import OrderStatusHistory
from app.model.product import Product
from app.payment.payment_code import build_payment_code
from app.service import product_stock

logger = logging.getLogger(__name__)

# Ten unique index chan 1 giao dich -> toi da 1 don.
DUPLICATE_TRANSACTION_CONSTRAINT = "uq_orders_transaction_id"


class DuplicateTransactionError(Exception):
    """Giao dich da duoc gan cho don khac (bi unique index DB chan)."""

    def __init__(self, transaction_id: str | None, order_code: str):
        super().__init__(
            f"Transaction {transaction_id} da duoc gan cho don khac, bo qua don {order_code}"
        )
        self.transaction_id = transaction_id
        self.order_code = order_code


def _is_duplicate_transaction(exc: IntegrityError) -> bool:
    """Loi `IntegrityError` co phai do unique index chong trung giao dich khong."""
    orig = getattr(exc, "orig", None)
    constraint = getattr(orig, "constraint_name", None) or ""
    if constraint == DUPLICATE_TRANSACTION_CONSTRAINT:
        return True
    # Driver khac khong expose `constraint_name` -> fallback theo message.
    return DUPLICATE_TRANSACTION_CONSTRAINT in str(orig) or (
        DUPLICATE_TRANSACTION_CONSTRAINT in str(exc)
    )


def _get_main_image_url(product: Product) -> str | None:
    """Lay URL anh chinh tu product.images_rel (is_main=True hoac position=0)."""
    if not product.images_rel:
        return None
    sorted_images = sorted(product.images_rel, key=lambda img: (not img.is_main, img.position))
    if not sorted_images:
        return None
    first = sorted_images[0]
    return first.secure_url


def generate_order_code() -> str:
    """
    Tao ma don hang unique theo dinh dang ma thanh toan cua SePay.

    Format: `<SEPAY_PAYMENT_CODE_PREFIX>` + `YYYYMMDD` + phan random, tong do dai
    hau to = `SEPAY_PAYMENT_CODE_SUFFIX_LENGTH` chu so. Dinh dang nay phai khop
    mau ma thanh toan khai bao tren dashboard SePay (xem `app.payment.payment_code`).
    """
    return build_payment_code()


def generate_tracking_code() -> str:
    """Tao ma tracking gia."""
    return f"TRK{random.randint(100000, 999999)}"


# Shipping fee rules
SHIPPING_FEE = Decimal("30000")  # 30,000 VND
FREE_SHIPPING_THRESHOLD = Decimal("500000")  # Free ship khi subtotal >= 500,000


async def get_order_by_id(db: AsyncSession, order_id: int) -> Order | None:
    """Lay order theo ID."""
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.status_history)
        )
        .where(Order.id == order_id)
    )
    return result.scalar_one_or_none()


async def get_order_by_code(db: AsyncSession, order_code: str) -> Order | None:
    """Lay order theo ma don."""
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.status_history)
        )
        .where(Order.order_code == order_code)
    )
    return result.scalar_one_or_none()


async def get_user_orders(
    db: AsyncSession,
    user_id: int,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Order], int]:
    """Lay danh sach don hang cua user."""
    query = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.status_history)
        )
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
    )
    
    count_query = select(func.count(Order.id)).where(Order.user_id == user_id)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    orders = list(result.scalars().all())
    
    return orders, total


async def get_all_orders(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    status: str | None = None,
    user_id: int | None = None,
) -> tuple[list[Order], int]:
    """Lay danh sach tat ca don hang (Admin)."""
    query = (
        select(Order)
        .options(
            selectinload(Order.items),
            selectinload(Order.status_history)
        )
    )
    
    count_query = select(func.count(Order.id))
    
    if status:
        query = query.where(Order.status == status)
        count_query = count_query.where(Order.status == status)
    
    if user_id:
        query = query.where(Order.user_id == user_id)
        count_query = count_query.where(Order.user_id == user_id)
    
    query = query.order_by(Order.created_at.desc())
    
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    orders = list(result.scalars().all())
    
    return orders, total


async def create_order(
    db: AsyncSession,
    user_id: int,
    items: list[dict[str, Any]],
    shipping_name: str,
    shipping_phone: str,
    shipping_address: str,
    payment_method: str,
    note: str | None = None,
) -> tuple[Order, dict | None]:
    """
    Tao don hang moi.
    
    Returns:
        Tuple of (order, qr_url) - qr_url only for SePay
    """
    # Validate and get products
    order_items = []
    subtotal = Decimal("0")
    
    for item in items:
        product = await db.execute(
            select(Product)
            .options(selectinload(Product.images_rel))
            .where(Product.id == item["product_id"])
            .with_for_update(of=Product)  # khoa dong de tranh oversell
        )
        product = product.scalar_one_or_none()
        
        if product is None:
            raise ValueError(f"Sản phẩm {item['product_id']} không tồn tại")
        
        if not product.is_active:
            raise ValueError(f"Sản phẩm {product.name} không còn bán")
        
        variant_id = item.get("variant_id")
        qty = item["qty"]

        # --- Chon bien the (neu co) ---
        variant_info = None
        variant = None
        if variant_id:
            if not product_stock.has_variants(product):
                raise ValueError(
                    f"Sản phẩm {product.name} không có phân loại nào"
                )
            variant = product_stock.find_variant(product, variant_id)
            if variant is None:
                raise ValueError(f"Variant {variant_id} không tồn tại")
            variant_info = {"id": variant["id"], "name": variant["name"]}
            # Check stock cua bien the
            if product_stock.variant_stock(variant) < qty:
                raise ValueError(
                    f"Sản phẩm {product.name} ({variant['name']}) không đủ stock"
                )
        elif product_stock.has_variants(product):
            # San pham co bien the -> phai chon cu the (xem docs/rules.md §7.3).
            # Neu cho qua, `products.stock` (gia tri dan xuat) se khong giam
            # duoc -> ban qua ton kho.
            raise ValueError(
                f"Sản phẩm {product.name} có nhiều phân loại, vui lòng chọn phân loại"
            )
        else:
            # San pham khong co bien the -> `products.stock` la nguon su that
            if product.stock < qty:
                raise ValueError(f"Sản phẩm {product.name} không đủ stock")

        # Calculate item subtotal
        if variant_info:
            item_price = float(
                variant.get("price")
                if variant.get("price") is not None
                else product.price
            )
        else:
            item_price = float(product.sale_price if product.sale_price else product.price)

        item_subtotal = Decimal(str(item_price)) * qty

        order_item = OrderItem(
            product_id=product.id,
            product_name=product.name,
            product_price=Decimal(str(item_price)),
            product_image=_get_main_image_url(product),
            variant_info=variant_info,
            qty=qty,
            subtotal=item_subtotal,
        )
        order_items.append(order_item)
        subtotal += item_subtotal

        # --- Cap nhat stock ---
        if variant is not None:
            # Nguon su that la stock cua bien the; `products.stock` se duoc
            # tinh lai = tong stock variants (khong tru truc tiep).
            variant["stock"] = product_stock.variant_stock(variant) - qty
            flag_modified(product, "variants")
            product_stock.recompute_stock(product)
        else:
            product.stock -= qty
    
    # Calculate shipping fee
    shipping_fee = Decimal("0") if subtotal >= FREE_SHIPPING_THRESHOLD else SHIPPING_FEE
    
    # Calculate total
    total = subtotal + shipping_fee
    
    # Generate order code
    order_code = generate_order_code()
    while await get_order_by_code(db, order_code):
        order_code = generate_order_code()
    
    # Create order
    order = Order(
        user_id=user_id,
        order_code=order_code,
        status="pending",
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        discount=Decimal("0"),
        total=total,
        payment_method=payment_method,
        payment_status="unpaid",
        shipping_name=shipping_name,
        shipping_phone=shipping_phone,
        shipping_address=shipping_address,
        note=note,
    )
    
    db.add(order)
    await db.flush()
    
    # Add items
    for item in order_items:
        item.order_id = order.id
        db.add(item)
    
    # Create status history
    history = OrderStatusHistory(
        order_id=order.id,
        status="pending",
        note="Đơn hàng được tạo",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(history)
    
    await db.commit()
    
    # Reload order with items
    order = await get_order_by_id(db, order.id)
    
    # Generate QR URL for SePay (dung provider abstraction)
    qr_url = None
    if payment_method == "sepay":
        from app.payment import get_provider

        provider = get_provider(payment_method)
        try:
            link = provider.create_payment_link(order)
            qr_url = link.qr_url
        except ValueError as exc:
            # Ma don khong khop mau ma SePay -> KHONG sinh QR sai (tranh mat tien).
            # Don van duoc tao; admin can sua cau hinh mau ma roi sinh lai QR.
            logger.error(
                "Khong tao duoc QR cho don %s: %s", order.order_code, exc
            )

    return order, qr_url


async def update_order_status(
    db: AsyncSession,
    order_id: int,
    new_status: str,
    note: str | None = None,
    updated_by: int | None = None,
    commit: bool = True,
) -> Order | None:
    """
    Cap nhat trang thai don hang.
    commit=False: chi flush, caller chiu trach nhiem commit (de gom vao 1 transaction).
    
    Valid transitions:
    - pending -> confirmed | cancelled
    - confirmed -> packing | cancelled
    - packing -> shipping
    - shipping -> delivered
    - delivered, cancelled = final
    """
    order = await get_order_by_id(db, order_id)
    if order is None:
        return None
    
    # Validate transition
    valid_transitions = {
        "pending": ["confirmed", "cancelled"],
        "confirmed": ["packing", "cancelled"],
        "packing": ["shipping"],
        "shipping": ["delivered"],
        "delivered": [],
        "cancelled": [],
    }
    
    if new_status not in valid_transitions.get(order.status, []):
        raise ValueError(f"Không thể chuyển từ {order.status} sang {new_status}")
    
    # Update status
    order.status = new_status
    
    # Auto-generate tracking code when shipping
    if new_status == "shipping" and not order.tracking_code:
        order.tracking_code = generate_tracking_code()
    
    # Auto-update payment_status for COD when delivered
    if new_status == "delivered" and order.payment_method == "cod":
        order.payment_status = "paid"

    # Tang sold_count khi don giao thanh cong
    if new_status == "delivered":
        for item in order.items:
            await db.execute(
                update(Product)
                .where(Product.id == item.product_id)
                .values(sold_count=Product.sold_count + item.qty)
            )
    
    # Create history
    history = OrderStatusHistory(
        order_id=order.id,
        status=new_status,
        note=note,
        created_by=updated_by,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(history)

    if not commit:
        await db.flush()
        return order

    await db.commit()
    await db.refresh(order)
    
    return await get_order_by_id(db, order.id)


async def cancel_order(
    db: AsyncSession,
    order_id: int,
    user_id: int,
) -> Order | None:
    """Huy don hang (User)."""
    order = await get_order_by_id(db, order_id)
    if order is None:
        return None
    
    # Verify ownership
    if order.user_id != user_id:
        raise ValueError("Không có quyền hủy đơn này")
    
    # Check if cancellable
    if order.status not in ["pending", "confirmed"]:
        raise ValueError("Không thể hủy đơn đang giao")
    
    # Doi trang thai + hoan stock trong cung 1 transaction
    try:
        order = await update_order_status(
            db, order_id, "cancelled", "Khách hàng hủy đơn", user_id, commit=False
        )

        for item in order.items:
            product = await db.execute(
                select(Product)
                .where(Product.id == item.product_id)
                .with_for_update()
            )
            product = product.scalar_one_or_none()

            if product:
                variant_id = item.variant_info.get("id") if item.variant_info else None
                if variant_id and product_stock.has_variants(product):
                    variant = product_stock.find_variant(product, variant_id)
                    if variant is not None:
                        variant["stock"] = product_stock.variant_stock(variant) + item.qty
                        flag_modified(product, "variants")
                        # `products.stock` = tong stock variants (gia tri dan xuat)
                        product_stock.recompute_stock(product)
                        continue

                # San pham khong co bien the (hoac bien the da bi xoa khoi
                # san pham) -> hoan stock truc tiep vao `products.stock`.
                product.stock += item.qty

        await db.commit()
    except Exception:
        await db.rollback()
        raise
    
    return await get_order_by_id(db, order_id)


async def update_payment_status(
    db: AsyncSession,
    order_code: str,
    transaction_id: str | None = None,
) -> Order | None:
    """
    Cap nhat trang thai thanh toan (webhook gateway).
    Idempotent: chi update neu chua paid; tu cho moi 1 transaction_id -> 1 don.

    Raises:
        DuplicateTransactionError: giao dich da duoc gan cho don khac. Do
            CHECK o tang application co race condition (2 request song song
            deu doc "khong thay duplicate" truoc khi ghi), unique index DB
            `uq_orders_transaction_id` la chot chong cuoi cung => loi nay
            phai duoc bat rieng, khong nuot chung vao loi 500.
    """
    order = await get_order_by_code(db, order_code)
    if order is None:
        return None

    # Idempotent - da paid roi thi skip
    if order.payment_status == "paid":
        return order

    # 1 giao dich khong duoc gan cho 2 don khac nhau
    if transaction_id:
        duplicate = await db.execute(
            select(Order).where(
                Order.transaction_id == transaction_id,
                Order.id != order.id,
            )
        )
        if duplicate.scalar_one_or_none() is not None:
            logger.warning(
                "Transaction %s da duoc gan cho don khac, bo qua don %s",
                transaction_id,
                order_code,
            )
            return order

    order.payment_status = "paid"
    order.paid_at = datetime.now(timezone.utc).isoformat()
    if transaction_id:
        order.transaction_id = transaction_id

    try:
        await db.commit()
    except IntegrityError as exc:
        # Unique index DB chan giao dich trung (race condition) -> rollback
        # va nem loi rieng de tang API tra 200 thay vi 500.
        await db.rollback()
        if _is_duplicate_transaction(exc):
            logger.warning(
                "Transaction %s bi DB chan trung (unique index), bo qua don %s",
                transaction_id,
                order_code,
            )
            raise DuplicateTransactionError(transaction_id, order_code) from exc
        raise

    return await get_order_by_id(db, order.id)


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
