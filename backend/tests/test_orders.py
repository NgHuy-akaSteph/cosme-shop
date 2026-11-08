"""Test luong don hang: tao don, vuot stock, huy don, chuyen trang thai, sold_count."""

import pytest

from tests.factories import *  # noqa: F401,F403 - nap fixture tu factories


def _payload(product_id: int, qty: int = 2, method: str = "cod") -> dict:
    return {
        "items": [{"product_id": product_id, "qty": qty}],
        "shipping_name": "Nguyen Van A",
        "shipping_phone": "0901234567",
        "shipping_address": "123 Duong ABC, Quan 1, TP.HCM",
        "payment_method": method,
    }


@pytest.mark.asyncio
async def test_create_order_cod_success(client, login, product):
    headers = await login("user@example.com", "user123")
    res = await client.post("/api/orders", json=_payload(product.id, 2), headers=headers)

    assert res.status_code == 201, res.text
    data = res.json()["data"]
    order = data["order"]

    # subtotal = sale_price * qty = 400000 * 2 = 800000; total = subtotal
    assert float(order["subtotal"]) == 800000.0
    assert float(order["total"]) == 800000.0
    assert order["payment_status"] == "unpaid"
    assert order["status"] == "pending"


@pytest.mark.asyncio
async def test_order_amounts_serialized_without_exponent(client, login, product):
    """Tien don phai la chuoi PHANG (vd "800000"), khong phai "8E+5"."""
    headers = await login("user@example.com", "user123")
    res = await client.post("/api/orders", json=_payload(product.id, 2), headers=headers)
    assert res.status_code == 201, res.text

    order = res.json()["data"]["order"]
    for field in ("subtotal", "discount_amount", "total"):
        value = order[field]
        assert isinstance(value, str), f"{field} phai la chuoi, nhan {type(value)}"
        assert "E" not in value.upper(), f"{field} chua ky hieu mu: {value}"

    assert order["total"] == "800000"

    for item in order["items"]:
        for field in ("product_price", "subtotal"):
            assert "E" not in str(item[field]).upper(), f"{field} chua ky hieu mu"


@pytest.mark.asyncio
async def test_create_order_insufficient_stock(client, login, product):
    headers = await login("user@example.com", "user123")
    res = await client.post("/api/orders", json=_payload(product.id, 50), headers=headers)

    assert res.status_code == 400, res.text
    body = res.json()
    assert "stock" in body["message"].lower()


@pytest.mark.asyncio
async def test_create_order_invalid_phone(client, login, product):
    headers = await login("user@example.com", "user123")
    payload = _payload(product.id)
    payload["shipping_phone"] = "abc"
    res = await client.post("/api/orders", json=payload, headers=headers)

    assert res.status_code == 400, res.text
    assert res.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_create_order_inactive_product(client, login, product, db_session):
    from sqlalchemy import update

    from app.model.product import Product

    await db_session.execute(
        update(Product).where(Product.id == product.id).values(is_active=False)
    )
    await db_session.commit()

    headers = await login("user@example.com", "user123")
    res = await client.post("/api/orders", json=_payload(product.id), headers=headers)

    assert res.status_code == 400, res.text
    assert "không còn bán" in res.json()["message"].lower()


@pytest.mark.asyncio
async def test_cancel_order_restores_stock(client, login, product, db_session):
    from sqlalchemy import select

    from app.model.product import Product

    headers = await login("user@example.com", "user123")
    original_stock = (
        await db_session.execute(
            select(Product.stock).where(Product.id == product.id)
        )
    ).scalar_one()

    create_res = await client.post(
        "/api/orders", json=_payload(product.id, 3), headers=headers
    )
    order_id = create_res.json()["data"]["order"]["id"]

    stock_after_order = (
        await db_session.execute(
            select(Product.stock).where(Product.id == product.id)
        )
    ).scalar_one()
    assert stock_after_order == original_stock - 3

    cancel_res = await client.post(f"/api/orders/{order_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200, cancel_res.text
    assert cancel_res.json()["data"]["status"] == "cancelled"

    stock_after_cancel = (
        await db_session.execute(
            select(Product.stock).where(Product.id == product.id)
        )
    ).scalar_one()
    assert stock_after_cancel == original_stock


@pytest.mark.asyncio
async def test_cancel_shipping_order_rejected(client, login, product):
    headers = await login("user@example.com", "user123")
    create_res = await client.post(
        "/api/orders", json=_payload(product.id), headers=headers
    )
    order_id = create_res.json()["data"]["order"]["id"]

    admin_headers = await login("admin@example.com", "admin123")
    for status in ("confirmed", "packing", "shipping"):
        res = await client.patch(
            f"/api/admin/orders/{order_id}/status",
            json={"status": status},
            headers=admin_headers,
        )
        assert res.status_code == 200, res.text

    cancel_res = await client.post(f"/api/orders/{order_id}/cancel", headers=headers)
    assert cancel_res.status_code == 400, cancel_res.text


@pytest.mark.asyncio
async def test_delivered_order_increments_sold_count(client, login, product, db_session):
    from sqlalchemy import select

    from app.model.product import Product

    headers = await login("user@example.com", "user123")
    create_res = await client.post(
        "/api/orders", json=_payload(product.id, 2), headers=headers
    )
    order_id = create_res.json()["data"]["order"]["id"]

    admin_headers = await login("admin@example.com", "admin123")
    for status in ("confirmed", "packing", "shipping", "delivered"):
        res = await client.patch(
            f"/api/admin/orders/{order_id}/status",
            json={"status": status},
            headers=admin_headers,
        )
        assert res.status_code == 200, res.text

    sold_count = (
        await db_session.execute(
            select(Product.sold_count).where(Product.id == product.id)
        )
    ).scalar_one()
    assert sold_count == 2


@pytest.mark.asyncio
async def test_invalid_status_transition_rejected(client, login, product):
    headers = await login("user@example.com", "user123")
    create_res = await client.post(
        "/api/orders", json=_payload(product.id), headers=headers
    )
    order_id = create_res.json()["data"]["order"]["id"]

    admin_headers = await login("admin@example.com", "admin123")
    # pending -> shipping khong hop le
    res = await client.patch(
        f"/api/admin/orders/{order_id}/status",
        json={"status": "shipping"},
        headers=admin_headers,
    )
    assert res.status_code == 400, res.text
    assert res.json()["code"] == "INVALID_STATUS_TRANSITION"
