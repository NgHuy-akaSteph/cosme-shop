"""Test ma giam gia (coupon).

Cover:
- Tinh tien giam: percent, fixed, clamp theo subtotal, tran `max_discount`.
- Validate: ma sai, het han, het luot, don duoi ngưỡng toi thieu.
- Dat hang: ap dung coupon hop le, tu choi coupon khong hop le.
- Bao mat: client gui `discount_amount` tu chon -> server bo qua.
- Atomic increment: het luot dung -> don bi tu choi.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio

from app.model.coupon import Coupon

from tests.factories import *  # noqa: F401,F403 - nap fixture tu factories


def _order_payload(product_id: int, qty: int = 1, **extra) -> dict:
    payload = {
        "items": [{"product_id": product_id, "qty": qty}],
        "shipping_name": "Nguyen Van A",
        "shipping_phone": "0901234567",
        "shipping_address": "123 Duong ABC, Quan 1, TP.HCM",
        "payment_method": "cod",
    }
    payload.update(extra)
    return payload


@pytest_asyncio.fixture
async def percent_coupon(db_session):
    """Ma giam 10%, giam toi da 100.000d."""
    coupon = Coupon(
        code="WELCOME10",
        discount_type="percent",
        discount_value=10,
        min_order_amount=0,
        max_discount=100000,
        max_uses=None,
        is_active=True,
    )
    db_session.add(coupon)
    await db_session.commit()
    await db_session.refresh(coupon)
    return coupon


@pytest_asyncio.fixture
async def fixed_coupon(db_session):
    """Ma giam cuoc 50.000d."""
    coupon = Coupon(
        code="FIXED50K",
        discount_type="fixed",
        discount_value=50000,
        min_order_amount=0,
        max_discount=None,
        max_uses=None,
        is_active=True,
    )
    db_session.add(coupon)
    await db_session.commit()
    await db_session.refresh(coupon)
    return coupon


# --- Tinh tien giam (unit) ---


@pytest.mark.asyncio
async def test_compute_discount_percent(percent_coupon):
    from app.service import discount_service

    amount = discount_service.compute_discount(percent_coupon, Decimal("400000"))
    # 10% cua 400.000 = 40.000 (chua cham tran 100.000)
    assert amount == Decimal("40000")


@pytest.mark.asyncio
async def test_compute_discount_percent_capped(percent_coupon):
    from app.service import discount_service

    # 10% cua 2.000.000 = 200.000 -> bi chan boi max_discount 100.000
    amount = discount_service.compute_discount(percent_coupon, Decimal("2000000"))
    assert amount == Decimal("100000")


@pytest.mark.asyncio
async def test_compute_discount_fixed(fixed_coupon):
    from app.service import discount_service

    amount = discount_service.compute_discount(fixed_coupon, Decimal("400000"))
    assert amount == Decimal("50000")


@pytest.mark.asyncio
async def test_compute_discount_never_exceeds_subtotal(fixed_coupon):
    from app.service import discount_service

    # Giam 50.000 tren don 30.000 -> clamp ve 30.000 (khong am)
    amount = discount_service.compute_discount(fixed_coupon, Decimal("30000"))
    assert amount == Decimal("30000")


@pytest.mark.asyncio
async def test_compute_discount_zero_subtotal(fixed_coupon):
    from app.service import discount_service

    amount = discount_service.compute_discount(fixed_coupon, Decimal("0"))
    assert amount == Decimal("0")


# --- Validate endpoint ---


@pytest.mark.asyncio
async def test_validate_coupon_success(client, login, percent_coupon):
    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/coupons/validate",
        json={"code": "welcome10", "subtotal": 400000},
        headers=headers,
    )

    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["code"] == "WELCOME10"
    assert data["discount_amount"] == 40000
    assert data["total"] == 360000


@pytest.mark.asyncio
async def test_validate_coupon_not_found(client, login):
    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/coupons/validate",
        json={"code": "NOPE", "subtotal": 400000},
        headers=headers,
    )

    assert res.status_code == 400, res.text
    assert res.json()["code"] == "INVALID_COUPON"


@pytest.mark.asyncio
async def test_validate_coupon_expired(client, login, db_session):
    coupon = Coupon(
        code="EXPIRED",
        discount_type="percent",
        discount_value=50,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        is_active=True,
    )
    db_session.add(coupon)
    await db_session.commit()

    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/coupons/validate",
        json={"code": "EXPIRED", "subtotal": 400000},
        headers=headers,
    )

    assert res.status_code == 400, res.text
    assert "hết hạn" in res.json()["message"]


@pytest.mark.asyncio
async def test_validate_coupon_inactive(client, login, db_session):
    coupon = Coupon(
        code="OFF",
        discount_type="percent",
        discount_value=50,
        is_active=False,
    )
    db_session.add(coupon)
    await db_session.commit()

    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/coupons/validate",
        json={"code": "OFF", "subtotal": 400000},
        headers=headers,
    )

    assert res.status_code == 400, res.text
    assert "ngừng hoạt động" in res.json()["message"]


@pytest.mark.asyncio
async def test_validate_coupon_min_amount_not_met(client, login, db_session):
    coupon = Coupon(
        code="BIGORDER",
        discount_type="percent",
        discount_value=10,
        min_order_amount=1000000,
        is_active=True,
    )
    db_session.add(coupon)
    await db_session.commit()

    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/coupons/validate",
        json={"code": "BIGORDER", "subtotal": 400000},
        headers=headers,
    )

    assert res.status_code == 400, res.text
    assert "tối thiểu" in res.json()["message"]


# --- Dat hang voi coupon ---


@pytest.mark.asyncio
async def test_create_order_with_coupon(client, login, product, percent_coupon):
    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/orders",
        json=_order_payload(product.id, coupon_code="WELCOME10"),
        headers=headers,
    )

    assert res.status_code == 201, res.text
    order = res.json()["data"]["order"]

    # sale_price 400.000 x 1 = 400.000 -> giam 10% = 40.000
    assert float(order["subtotal"]) == 400000.0
    assert float(order["discount_amount"]) == 40000.0
    assert float(order["total"]) == 360000.0
    assert order["discount_code"] == "WELCOME10"


@pytest.mark.asyncio
async def test_create_order_without_coupon(client, login, product):
    headers = await login("user@example.com", "user123")
    res = await client.post("/api/orders", json=_order_payload(product.id), headers=headers)

    assert res.status_code == 201, res.text
    order = res.json()["data"]["order"]
    assert float(order["discount_amount"]) == 0.0
    assert float(order["total"]) == float(order["subtotal"])
    assert order["discount_code"] is None


@pytest.mark.asyncio
async def test_create_order_invalid_coupon_rejected(client, login, product):
    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/orders",
        json=_order_payload(product.id, coupon_code="NOPE"),
        headers=headers,
    )

    assert res.status_code == 400, res.text
    assert "Mã giảm giá" in res.json()["message"]


@pytest.mark.asyncio
async def test_create_order_ignores_client_discount_amount(
    client, login, product, percent_coupon
):
    """Client tu gui `discount_amount` -> server KHONG tin, tu tinh lai."""
    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/orders",
        json=_order_payload(
            product.id,
            coupon_code="WELCOME10",
            discount_amount=999999999,
        ),
        headers=headers,
    )

    assert res.status_code == 201, res.text
    order = res.json()["data"]["order"]
    # Server tinh lai: 10% cua 400.000 = 40.000 (khong phai 999.999.999)
    assert float(order["discount_amount"]) == 40000.0
    assert float(order["total"]) == 360000.0


@pytest.mark.asyncio
async def test_coupon_used_count_incremented(
    client, login, product, db_session, percent_coupon
):
    headers = await login("user@example.com", "user123")
    await client.post(
        "/api/orders",
        json=_order_payload(product.id, coupon_code="WELCOME10"),
        headers=headers,
    )

    await db_session.refresh(percent_coupon)
    assert percent_coupon.used_count == 1


@pytest.mark.asyncio
async def test_coupon_exhausted_rejects_new_order(
    client, login, product, db_session
):
    """Ma het luot -> don moi bi tu choi (rollback luot dung)."""
    coupon = Coupon(
        code="ONESHOT",
        discount_type="percent",
        discount_value=50,
        max_uses=1,
        is_active=True,
    )
    db_session.add(coupon)
    await db_session.commit()
    await db_session.refresh(coupon)

    headers = await login("user@example.com", "user123")

    first = await client.post(
        "/api/orders",
        json=_order_payload(product.id, coupon_code="ONESHOT"),
        headers=headers,
    )
    assert first.status_code == 201, first.text

    second = await client.post(
        "/api/orders",
        json=_order_payload(product.id, coupon_code="ONESHOT"),
        headers=headers,
    )
    assert second.status_code == 400, second.text
    assert "hết lượt" in second.json()["message"]


@pytest.mark.asyncio
async def test_order_keeps_discount_snapshot_after_coupon_deleted(
    client, login, product, db_session, percent_coupon
):
    """Xoa coupon sau -> lich su don van giu ma + so tien giam."""
    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/orders",
        json=_order_payload(product.id, coupon_code="WELCOME10"),
        headers=headers,
    )
    assert res.status_code == 201, res.text
    order_id = res.json()["data"]["order"]["id"]

    # Admin xoa coupon
    await db_session.delete(percent_coupon)
    await db_session.commit()

    detail = await client.get(f"/api/orders/{order_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    order = detail.json()["data"]
    assert order["discount_code"] == "WELCOME10"
    assert float(order["discount_amount"]) == 40000.0


# --- Admin CRUD ---


@pytest.mark.asyncio
async def test_admin_create_coupon(client, login):
    admin_headers = await login("admin@example.com", "admin123")
    res = await client.post(
        "/api/admin/coupons",
        json={
            "code": "newsale",
            "discount_type": "percent",
            "discount_value": "20",
            "max_discount": 50000,
        },
        headers=admin_headers,
    )

    assert res.status_code == 201, res.text
    data = res.json()["data"]
    # Code duoc chuan hoa thanh HOA
    assert data["code"] == "NEWSALE"
    assert data["discount_value"] == 20


@pytest.mark.asyncio
async def test_admin_create_duplicate_coupon_rejected(client, login, percent_coupon):
    admin_headers = await login("admin@example.com", "admin123")
    res = await client.post(
        "/api/admin/coupons",
        json={
            "code": "WELCOME10",
            "discount_type": "percent",
            "discount_value": 10,
        },
        headers=admin_headers,
    )

    assert res.status_code == 400, res.text
    assert "đã tồn tại" in res.json()["message"]


@pytest.mark.asyncio
async def test_admin_coupon_list_requires_admin(client, login):
    user_headers = await login("user@example.com", "user123")
    res = await client.get("/api/admin/coupons", headers=user_headers)
    assert res.status_code == 403, res.text


@pytest.mark.asyncio
async def test_admin_update_coupon_allows_clearing_max_discount(client, login, percent_coupon):
    """Set `max_discount = null` = bo tran giam (khong phai "khong doi")."""
    admin_headers = await login("admin@example.com", "admin123")
    res = await client.patch(
        f"/api/admin/coupons/{percent_coupon.id}",
        json={"max_discount": None},
        headers=admin_headers,
    )

    assert res.status_code == 200, res.text
    assert res.json()["data"]["max_discount"] is None


@pytest.mark.asyncio
async def test_admin_update_coupon_rejects_percent_over_100(client, login, percent_coupon):
    """Coupon dang percent 10% -> admin doi value 150 -> phai bao loi."""
    admin_headers = await login("admin@example.com", "admin123")
    res = await client.patch(
        f"/api/admin/coupons/{percent_coupon.id}",
        json={"discount_value": 150},
        headers=admin_headers,
    )

    assert res.status_code == 400, res.text
    assert "100" in res.json()["message"]


@pytest.mark.asyncio
async def test_admin_update_coupon_switch_to_fixed(client, login, percent_coupon):
    """Doi tu percent sang fixed -> validate tren gia tri hieu luc."""
    admin_headers = await login("admin@example.com", "admin123")
    res = await client.patch(
        f"/api/admin/coupons/{percent_coupon.id}",
        json={"discount_type": "fixed", "discount_value": 30000},
        headers=admin_headers,
    )

    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["discount_type"] == "fixed"
    assert data["discount_value"] == 30000


@pytest.mark.asyncio
async def test_stock_not_persisted_when_coupon_invalid(
    client, login, product, engine
):
    """Coupon sai -> don khong tao, stock decrement khong duoc commit."""
    from sqlalchemy import select

    from app.model.product import Product
    from sqlalchemy.ext.asyncio import AsyncSession

    product_id = product.id
    original_stock = product.stock

    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/orders",
        json=_order_payload(product_id, coupon_code="KHONG_CO"),
        headers=headers,
    )
    assert res.status_code == 400, res.text

    # Doc bang session RIENG: session cua app chua rollback nen khong the
    # phan bi commit that. Session moi chi thay gia tri da COMMIT.
    async with AsyncSession(bind=engine) as session:
        stock_after = (
            await session.execute(
                select(Product.stock).where(Product.id == product_id)
            )
        ).scalar_one()

    assert stock_after == original_stock


@pytest.mark.asyncio
async def test_coupon_usage_rolled_back_when_coupon_exhausted(
    client, login, product, db_session
):
    """Ma het luot -> don moi bi tu choi va KHONG tang them luot dung."""
    coupon = Coupon(
        code="LIMIT1",
        discount_type="percent",
        discount_value=50,
        max_uses=1,
        is_active=True,
    )
    db_session.add(coupon)
    await db_session.commit()
    await db_session.refresh(coupon)

    headers = await login("user@example.com", "user123")

    first = await client.post(
        "/api/orders",
        json=_order_payload(product.id, coupon_code="LIMIT1"),
        headers=headers,
    )
    assert first.status_code == 201, first.text

    second = await client.post(
        "/api/orders",
        json=_order_payload(product.id, coupon_code="LIMIT1"),
        headers=headers,
    )
    assert second.status_code == 400, second.text

    await db_session.refresh(coupon)
    # Luot dung phai dung bang 1 (khong bi tang them do don bi rollback)
    assert coupon.used_count == 1


@pytest.mark.asyncio
async def test_admin_delete_coupon(client, login, percent_coupon):
    admin_headers = await login("admin@example.com", "admin123")
    res = await client.delete(
        f"/api/admin/coupons/{percent_coupon.id}", headers=admin_headers
    )
    assert res.status_code == 204, res.text
