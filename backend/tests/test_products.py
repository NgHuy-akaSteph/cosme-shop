"""Test san pham: filter OR, update null, phan quyen, soft delete."""

import pytest

from tests.factories import *  # noqa: F401,F403 - nap fixture tu factories


@pytest.mark.asyncio
async def test_filter_skin_types_or_semantics(client, product, other_product):
    """Chon 2 loai da -> tra san pham khop MOT trong hai (OR, khong phai AND)."""
    res = await client.get("/api/products?skin_types=oily,combination")
    assert res.status_code == 200, res.text

    ids = {p["id"] for p in res.json()["data"]}
    assert product.id in ids          # oily
    assert other_product.id in ids    # combination
    assert res.json()["total"] >= 2


@pytest.mark.asyncio
async def test_filter_concerns_or_semantics(client, product, other_product):
    res = await client.get("/api/products?concerns=acne,aging")
    assert res.status_code == 200, res.text

    ids = {p["id"] for p in res.json()["data"]}
    assert product.id in ids          # acne
    assert other_product.id in ids    # aging


@pytest.mark.asyncio
async def test_filter_single_skin_type(client, product, other_product):
    res = await client.get("/api/products?skin_types=oily")
    ids = {p["id"] for p in res.json()["data"]}
    assert product.id in ids
    assert other_product.id not in ids


@pytest.mark.asyncio
async def test_update_product_allows_null_sale_price(client, login, product):
    headers = await login("admin@example.com", "admin123")
    res = await client.patch(
        f"/api/products/{product.id}", json={"sale_price": None}, headers=headers
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["sale_price"] is None

    get_res = await client.get(f"/api/products/{product.id}")
    assert get_res.json()["data"]["sale_price"] is None


@pytest.mark.asyncio
async def test_update_product_allows_null_description(client, login, product):
    headers = await login("admin@example.com", "admin123")
    res = await client.patch(
        f"/api/products/{product.id}", json={"description": None}, headers=headers
    )
    assert res.status_code == 200, res.text
    assert res.json()["data"]["description"] is None


@pytest.mark.asyncio
async def test_update_product_ignores_non_nullable_none(client, login, product):
    """Khong cho gan None cho field bat buoc (price)."""
    headers = await login("admin@example.com", "admin123")
    res = await client.patch(
        f"/api/products/{product.id}", json={"price": None}, headers=headers
    )
    assert res.status_code == 400, res.text


@pytest.mark.asyncio
async def test_public_list_hides_inactive(client, product, db_session):
    from sqlalchemy import update

    from app.model.product import Product

    await db_session.execute(
        update(Product).where(Product.id == product.id).values(is_active=False)
    )
    await db_session.commit()

    res = await client.get("/api/products")
    ids = {p["id"] for p in res.json()["data"]}
    assert product.id not in ids


@pytest.mark.asyncio
async def test_admin_create_product(client, login, category, brand):
    headers = await login("admin@example.com", "admin123")
    res = await client.post(
        "/api/products",
        json={
            "name": "New Product",
            "price": 300000,
            "stock": 7,
            "category_id": category.id,
            "brand_id": brand.id,
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    assert res.json()["data"]["id"] > 0


@pytest.mark.asyncio
async def test_regular_user_cannot_create_product(client, login):
    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/products",
        json={"name": "Hack", "price": 1, "stock": 1, "category_id": 1, "brand_id": 1},
        headers=headers,
    )
    assert res.status_code == 403, res.text


@pytest.mark.asyncio
async def test_product_price_serialized_without_exponent(client, product):
    """Gia phai la chuoi PHANG (vd "500000"), khong phai kho hoc "5E+5".

    `str(Decimal)` tu Postgres sinh "5E+5" -> FE `InputNumber` khong parse
    duoc -> hien thi sai ("1E") trong form Admin.
    """
    res = await client.get(f"/api/products/{product.id}")
    assert res.status_code == 200, res.text

    data = res.json()["data"]
    for field in ("price", "sale_price"):
        value = data[field]
        assert isinstance(value, str), f"{field} phai la chuoi, nhan {type(value)}"
        assert "E" not in value.upper(), f"{field} chua ky hieu mu: {value}"
        assert float(value) == float(data[field])  # parse duoc thanh so


@pytest.mark.asyncio
async def test_product_list_price_serialized_without_exponent(client, product):
    res = await client.get("/api/products")
    assert res.status_code == 200, res.text

    item = next(p for p in res.json()["data"] if p["id"] == product.id)
    assert item["price"] == "500000"
    assert item["sale_price"] == "400000"


@pytest.mark.asyncio
async def test_admin_users_total_is_correct(client, login, admin_user, normal_user):
    headers = await login("admin@example.com", "admin123")
    res = await client.get("/api/admin/users?size=1", headers=headers)
    assert res.status_code == 200, res.text

    body = res.json()
    assert len(body["data"]) == 1
    assert body["total"] == 2  # khong phai len(data)


@pytest.mark.asyncio
async def test_admin_stats_endpoint(client, login, product):
    headers = await login("admin@example.com", "admin123")
    res = await client.get("/api/admin/stats", headers=headers)
    assert res.status_code == 200, res.text

    data = res.json()["data"]
    for key in (
        "total_revenue",
        "orders_by_status",
        "revenue_by_day",
        "top_products",
        "low_stock",
    ):
        assert key in data


@pytest.mark.asyncio
async def test_admin_stats_requires_admin(client, login):
    res = await client.get("/api/admin/stats")
    assert res.status_code == 401, res.text

    user_headers = await login("user@example.com", "user123")
    res = await client.get("/api/admin/stats", headers=user_headers)
    assert res.status_code == 403, res.text
