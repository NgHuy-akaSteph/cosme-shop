"""Stats service - so lieu thong ke cho admin dashboard"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.money import format_money
from app.model.order import Order
from app.model.order_item import OrderItem
from app.model.product import Product
from app.model.user import User

LOW_STOCK_THRESHOLD = 10


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

    # Doanh thu chua thu (COD chua giao)
    pending_revenue = (
        await db.execute(
            select(func.coalesce(func.sum(Order.total), 0)).where(
                Order.payment_status == "unpaid", Order.status != "cancelled"
            )
        )
    ).scalar_one()

    # Don theo trang thai
    status_rows = await db.execute(
        select(Order.status, func.count(Order.id)).group_by(Order.status)
    )
    orders_by_status = {status: count for status, count in status_rows.all()}

    # Doanh thu theo ngay (chi don da thanh toan)
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
        {"day": str(row.day), "revenue": format_money(row.revenue), "orders": row.orders}
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
        {"name": r.product_name, "qty": r.qty, "revenue": format_money(r.revenue)}
        for r in top_rows.all()
    ]

    # San pham sap het hang
    low_stock_rows = await db.execute(
        select(Product.id, Product.name, Product.stock, Product.sale_price, Product.price)
        .where(Product.is_active == True, Product.stock <= LOW_STOCK_THRESHOLD)
        .order_by(Product.stock.asc())
        .limit(10)
    )
    low_stock = [
        {
            "id": r.id,
            "name": r.name,
            "stock": r.stock,
            "price": format_money(r.sale_price or r.price),
        }
        for r in low_stock_rows.all()
    ]

    total_products = (
        await db.execute(select(func.count(Product.id)).where(Product.is_active == True))
    ).scalar_one()
    total_users = (await db.execute(select(func.count(User.id)))).scalar_one()

    return {
        "total_orders": total_orders,
        "total_revenue": format_money(revenue),
        "pending_revenue": format_money(pending_revenue),
        "total_products": total_products,
        "total_users": total_users,
        "orders_by_status": orders_by_status,
        "revenue_by_day": revenue_by_day,
        "top_products": top_products,
        "low_stock": low_stock,
    }
