"""Test stock: 1 nguon su that duy nhat cho san pham co bien the.

Quy tac (xem `app/service/product_stock.py`):
- San pham co variants -> `variants[i].stock` la nguon su that,
  `products.stock` = tong stock variants (gia tri dan xuat).
- San pham khong co variants -> `products.stock` la nguon su that.
"""

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.model.product import Product

from tests.factories import *  # noqa: F401,F403 - nap fixture tu factories


def _variants() -> list[dict]:
    return [
        {"id": "v1", "name": "Do Ruby", "price": 350000, "stock": 20},
        {"id": "v2", "name": "Do Hong", "price": 320000, "stock": 5},
    ]


def _order_payload(product_id: int, variant_id: str | None, qty: int = 1) -> dict:
    item = {"product_id": product_id, "qty": qty}
    if variant_id is not None:
        item["variant_id"] = variant_id
    return {
        "items": [item],
        "shipping_name": "Nguyen Van A",
        "shipping_phone": "0901234567",
        "shipping_address": "123 Duong ABC, Quan 1, TP.HCM",
        "payment_method": "cod",
    }


async def _reload(db_session, product_id: int) -> Product:
    return (
        await db_session.execute(
            select(Product).where(Product.id == product_id)
        )
    ).scalar_one()


@pytest_asyncio.fixture
async def product_with_variants(db_session, category, brand):
    """San pham co 2 bien the (stock 20 + 5 = 25) -> `products.stock` = 25."""
    prod = Product(
        name="Son Moi Co Variants",
        slug="son-moi-co-variants",
        description="San pham co bien the",
        price=Decimal("300000"),
        sale_price=None,
        stock=25,
        category_id=category.id,
        brand_id=brand.id,
        variants=_variants(),
        sold_count=0,
        rating_avg=Decimal("0"),
        rating_count=0,
        is_active=True,
    )
    db_session.add(prod)
    await db_session.commit()
    await db_session.refresh(prod)
    return prod


# ---product_stock helpers --------------------------------------------------


def test_total_variant_stock_sums_variants(product_with_variants):
    from app.service import product_stock

    assert product_stock.total_variant_stock(product_with_variants) == 25


def test_variant_stock_handles_null(product_with_variants):
    from app.service import product_stock

    assert product_stock.variant_stock({"id": "x", "stock": None}) == 0
    assert product_stock.variant_stock({"id": "x"}) == 0
    assert product_stock.variant_stock({"id": "x", "stock": 7}) == 7


def test_recompute_stock_overwrites_product_stock(product_with_variants):
    """`products.stock` phai = tong stock variants, khong phai con so cu."""
    from app.service import product_stock

    product_with_variants.stock = 999  # admin nhap tay lech
    product_stock.recompute_stock(product_with_variants)

    assert product_with_variants.stock == 25


def test_recompute_stock_keeps_stock_without_variants(product):
    """San pham khong co variants -> giu nguyen `products.stock`."""
    from app.service import product_stock

    product.stock = 42
    product_stock.recompute_stock(product)

    assert product.stock == 42


# --- API: dong bo stock khi admin tao/sua san pham ------------------------


@pytest.mark.asyncio
async def test_create_product_recomputes_stock(client, login, category, brand):
    """Admin tao san pham co bien the -> `stock` = tong stock variants."""
    headers = await login("admin@example.com", "admin123")
    res = await client.post(
        "/api/products",
        json={
            "name": "Son Moi Moi",
            "price": 300000,
            "stock": 999,  # gia tri nhap tay -> bi dan xuat ghi de
            "category_id": category.id,
            "brand_id": brand.id,
            "variants": _variants(),
        },
        headers=headers,
    )

    assert res.status_code == 201, res.text
    assert res.json()["data"]["stock"] == 25


@pytest.mark.asyncio
async def test_update_product_variants_recomputes_stock(
    client, login, product_with_variants
):
    """Admin them bien the -> `products.stock` duoc tinh lai."""
    headers = await login("admin@example.com", "admin123")
    res = await client.patch(
        f"/api/products/{product_with_variants.id}",
        json={
            "variants": [
                {"id": "v1", "name": "Do Ruby", "price": 350000, "stock": 10},
                {"id": "v2", "name": "Do Hong", "price": 320000, "stock": 3},
                {"id": "v3", "name": "Nude", "price": 330000, "stock": 7},
            ]
        },
        headers=headers,
    )

    assert res.status_code == 200, res.text
    assert res.json()["data"]["stock"] == 20  # 10 + 3 + 7


@pytest.mark.asyncio
async def test_api_stock_reflects_variants_not_stale_column(
    client, product_with_variants, db_session
):
    """`products.stock` cu trong DB -> API van tra tong stock variants."""
    from sqlalchemy import update

    # Mo phong admin sua truc tiep DB (hoac du lieu seed cu)
    await db_session.execute(
        update(Product)
        .where(Product.id == product_with_variants.id)
        .values(stock=0)
    )
    await db_session.commit()

    res = await client.get(f"/api/products/{product_with_variants.id}")
    assert res.status_code == 200, res.text
    assert res.json()["data"]["stock"] == 25


# --- Order: chi 1 nguon stock bi tru ---------------------------------------


@pytest.mark.asyncio
async def test_order_decrements_only_variant_stock(
    client, login, product_with_variants, db_session
):
    """Dat 3 san pham v1 -> v1 giam 3, v2 giu nguyen, tong stock giam 3."""
    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/orders",
        json=_order_payload(product_with_variants.id, "v1", qty=3),
        headers=headers,
    )
    assert res.status_code == 201, res.text

    product = await _reload(db_session, product_with_variants.id)
    v1 = next(v for v in product.variants if v["id"] == "v1")
    v2 = next(v for v in product.variants if v["id"] == "v2")

    assert v1["stock"] == 17
    assert v2["stock"] == 5  # bien the khac khong bi tru
    assert product.stock == 22  # dan xuat = 17 + 5


@pytest.mark.asyncio
async def test_order_without_variant_id_rejected(
    client, login, product_with_variants
):
    """San pham co bien the -> phai chon bien the, khong cho dat chung."""
    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/orders",
        json=_order_payload(product_with_variants.id, None, qty=1),
        headers=headers,
    )

    assert res.status_code == 400, res.text
    assert "phân loại" in res.json()["message"].lower()


@pytest.mark.asyncio
async def test_order_variant_id_on_product_without_variants_rejected(
    client, login, product
):
    """San pham khong co bien the nhung client gui `variant_id` -> 400."""
    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/orders",
        json=_order_payload(product.id, "v1", qty=1),
        headers=headers,
    )

    assert res.status_code == 400, res.text
    assert "không có phân loại" in res.json()["message"].lower()


@pytest.mark.asyncio
async def test_cancel_restores_only_variant_stock(
    client, login, product_with_variants, db_session
):
    """Huy don -> chi hoan lai bien the da mua."""
    headers = await login("user@example.com", "user123")
    create_res = await client.post(
        "/api/orders",
        json=_order_payload(product_with_variants.id, "v1", qty=3),
        headers=headers,
    )
    order_id = create_res.json()["data"]["order"]["id"]

    cancel_res = await client.post(f"/api/orders/{order_id}/cancel", headers=headers)
    assert cancel_res.status_code == 200, cancel_res.text

    product = await _reload(db_session, product_with_variants.id)
    v1 = next(v for v in product.variants if v["id"] == "v1")
    v2 = next(v for v in product.variants if v["id"] == "v2")

    assert v1["stock"] == 20
    assert v2["stock"] == 5
    assert product.stock == 25


@pytest.mark.asyncio
async def test_product_without_variants_still_uses_product_stock(
    client, login, product, db_session
):
    """San pham thuong: chi tru `products.stock`."""
    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/orders",
        json=_order_payload(product.id, None, qty=2),
        headers=headers,
    )
    assert res.status_code == 201, res.text

    reloaded = await _reload(db_session, product.id)
    assert reloaded.stock == 8  # 10 - 2
