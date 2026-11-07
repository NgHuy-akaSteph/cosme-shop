"""Test bien the (variants) san pham: validate input, tinh gia, tru/hoan stock."""

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.model.product import Product

from tests.factories import *  # noqa: F401,F403 - nap fixture tu factories


def _variants_payload() -> list[dict]:
    return [
        {"id": "v1", "name": "Do Ruby", "price": 350000, "stock": 20},
        {"id": "v2", "name": "Do Hồng", "price": 320000, "stock": 5},
    ]


def _product_payload(category_id: int, brand_id: int, **overrides) -> dict:
    payload = {
        "name": "Son Moi Mat",
        "price": 300000,
        "stock": 25,
        "category_id": category_id,
        "brand_id": brand_id,
    }
    payload.update(overrides)
    return payload


def _order_payload(product_id: int, variant_id: str, qty: int = 1) -> dict:
    return {
        "items": [
            {"product_id": product_id, "variant_id": variant_id, "qty": qty}
        ],
        "shipping_name": "Nguyen Van A",
        "shipping_phone": "0901234567",
        "shipping_address": "123 Duong ABC, Quan 1, TP.HCM",
        "payment_method": "cod",
    }


@pytest_asyncio.fixture
async def product_with_variants(db_session, category, brand):
    """San pham co 2 bien the, moi bien the gia + stock rieng."""
    prod = Product(
        name="Son Moi Co Variants",
        slug="son-moi-co-variants",
        description="San pham co bien the",
        price=Decimal("300000"),
        sale_price=None,
        stock=25,
        category_id=category.id,
        brand_id=brand.id,
        variants=_variants_payload(),
        sold_count=0,
        rating_avg=Decimal("0"),
        rating_count=0,
        is_active=True,
    )
    db_session.add(prod)
    await db_session.commit()
    await db_session.refresh(prod)
    return prod


# --- Validation input tu admin ---------------------------------------------


@pytest.mark.asyncio
async def test_create_product_with_valid_variants(client, login, category, brand):
    """Admin tao san pham co bien the -> bien the duoc luu dung cau truc."""
    headers = await login("admin@example.com", "admin123")
    res = await client.post(
        "/api/products",
        json=_product_payload(
            category.id, brand.id, variants=_variants_payload()
        ),
        headers=headers,
    )

    assert res.status_code == 201, res.text
    variants = res.json()["data"]["variants"]
    assert len(variants) == 2
    assert variants[0]["id"] == "v1"
    assert variants[0]["name"] == "Do Ruby"
    assert variants[0]["stock"] == 20


@pytest.mark.asyncio
async def test_create_product_variant_missing_id_rejected(client, login, category, brand):
    headers = await login("admin@example.com", "admin123")
    res = await client.post(
        "/api/products",
        json=_product_payload(category.id, brand.id, variants=[{"name": "Do Ruby"}]),
        headers=headers,
    )

    assert res.status_code == 400, res.text
    assert res.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_create_product_duplicate_variant_id_rejected(client, login, category, brand):
    """Trung `id` se lam cart key product_id + variant_id bi collision."""
    headers = await login("admin@example.com", "admin123")
    res = await client.post(
        "/api/products",
        json=_product_payload(
            category.id,
            brand.id,
            variants=[
                {"id": "v1", "name": "A", "price": 1, "stock": 1},
                {"id": "v1", "name": "B", "price": 1, "stock": 1},
            ],
        ),
        headers=headers,
    )

    assert res.status_code == 400, res.text
    assert "trùng" in res.json()["message"].lower()


@pytest.mark.asyncio
async def test_create_product_negative_variant_price_rejected(
    client, login, category, brand
):
    headers = await login("admin@example.com", "admin123")
    res = await client.post(
        "/api/products",
        json=_product_payload(
            category.id,
            brand.id,
            variants=[{"id": "v1", "name": "A", "price": -1, "stock": 1}],
        ),
        headers=headers,
    )

    assert res.status_code == 400, res.text


@pytest.mark.asyncio
async def test_update_product_variants_to_null(client, login, product):
    """Xoa het bien the -> variants = null."""
    headers = await login("admin@example.com", "admin123")
    res = await client.patch(
        f"/api/products/{product.id}", json={"variants": None}, headers=headers
    )

    assert res.status_code == 200, res.text
    assert res.json()["data"]["variants"] is None


# --- Order voi bien the ----------------------------------------------------


@pytest.mark.asyncio
async def test_order_uses_variant_price(client, login, product_with_variants):
    """Gia tinh theo bien the, khong dung price/sale_price cua product."""
    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/orders",
        json=_order_payload(product_with_variants.id, "v1", qty=2),
        headers=headers,
    )

    assert res.status_code == 201, res.text
    order = res.json()["data"]["order"]

    # 350000 * 2 = 700000
    assert float(order["subtotal"]) == 700000.0
    assert float(order["total"]) == 700000.0


@pytest.mark.asyncio
async def test_order_snapshots_variant_info(client, login, product_with_variants):
    """Order item luu snapshot {id, name} cua bien the."""
    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/orders",
        json=_order_payload(product_with_variants.id, "v2", qty=1),
        headers=headers,
    )

    assert res.status_code == 201, res.text
    items = res.json()["data"]["order"]["items"]
    assert len(items) == 1
    assert items[0]["variant_info"] == {"id": "v2", "name": "Do Hồng"}


@pytest.mark.asyncio
async def test_order_unknown_variant_rejected(client, login, product_with_variants):
    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/orders",
        json=_order_payload(product_with_variants.id, "v99", qty=1),
        headers=headers,
    )

    assert res.status_code == 400, res.text
    assert "không tồn tại" in res.json()["message"].lower()


@pytest.mark.asyncio
async def test_order_variant_insufficient_stock_rejected(
    client, login, product_with_variants
):
    """v2 chi con 5 stock -> dat 6 phai fail (khong fallback sang stock product)."""
    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/orders",
        json=_order_payload(product_with_variants.id, "v2", qty=6),
        headers=headers,
    )

    assert res.status_code == 400, res.text
    assert "stock" in res.json()["message"].lower()


@pytest.mark.asyncio
async def test_order_decrements_variant_stock(client, login, product_with_variants, db_session):
    """Dat hang -> stock cua bien the giam, stock product cung giam."""
    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/orders",
        json=_order_payload(product_with_variants.id, "v1", qty=3),
        headers=headers,
    )
    assert res.status_code == 201, res.text

    product = (
        await db_session.execute(
            select(Product).where(Product.id == product_with_variants.id)
        )
    ).scalar_one()

    v1 = next(v for v in product.variants if v["id"] == "v1")
    assert v1["stock"] == 17  # 20 - 3
    assert product.stock == 22  # 25 - 3


@pytest.mark.asyncio
async def test_cancel_order_restores_variant_stock(
    client, login, product_with_variants, db_session
):
    """Huy don -> hoan lai stock cua bien the."""
    headers = await login("user@example.com", "user123")
    create_res = await client.post(
        "/api/orders",
        json=_order_payload(product_with_variants.id, "v1", qty=3),
        headers=headers,
    )
    order_id = create_res.json()["data"]["order"]["id"]

    cancel_res = await client.post(f"/api/orders/{order_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200, cancel_res.text

    product = (
        await db_session.execute(
            select(Product).where(Product.id == product_with_variants.id)
        )
    ).scalar_one()

    v1 = next(v for v in product.variants if v["id"] == "v1")
    assert v1["stock"] == 20  # hoan lai 3
    assert product.stock == 25
