"""Fixture du dung chung: tao user, product, token."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio

from app.core.security import hash_password
from app.model.brand import Brand
from app.model.category import Category
from app.model.product import Product
from app.model.user import User


@pytest_asyncio.fixture
async def admin_user(db_session):
    user = User(
        email="admin@example.com",
        password_hash=hash_password("admin123"),
        full_name="Admin Test",
        phone="0900000000",
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def normal_user(db_session):
    user = User(
        email="user@example.com",
        password_hash=hash_password("user123"),
        full_name="User Test",
        phone="0900123456",
        address="123 Đường ABC, Quận 1, TP. Hồ Chí Minh",
        role="user",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def login(client, admin_user, normal_user):
    """Helper login tra ve dict Authorization.

    Fixture nay phu thuoc `admin_user` + `normal_user` de dam bao
    du lieu nguoi dung ton tai trong DB test.
    """

    async def _login(email: str, password: str) -> dict:
        res = await client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )
        assert res.status_code == 200, res.text
        return {"Authorization": f"Bearer {res.json()['data']['access_token']}"}

    return _login


@pytest_asyncio.fixture
async def category(db_session):
    cat = Category(
        name="Skincare",
        slug="skincare-test",
        description="Danh muc test",
    )
    db_session.add(cat)
    await db_session.commit()
    await db_session.refresh(cat)
    return cat


@pytest_asyncio.fixture
async def brand(db_session):
    br = Brand(
        name="TestBrand",
        slug="test-brand",
        description="Thuong hieu test",
        logo_url=None,
    )
    db_session.add(br)
    await db_session.commit()
    await db_session.refresh(br)
    return br


@pytest_asyncio.fixture
async def product(db_session, category, brand):
    prod = Product(
        name="Serum Test",
        slug="serum-test",
        description="Mo ta san pham test",
        price=Decimal("500000"),
        sale_price=Decimal("400000"),
        stock=10,
        category_id=category.id,
        brand_id=brand.id,
        skin_types=["oily", "dry"],
        concerns=["acne"],
        key_ingredients=["Niacinamide"],
        free_from=None,
        variants=None,
        sold_count=0,
        rating_avg=Decimal("0"),
        rating_count=0,
        is_active=True,
    )
    db_session.add(prod)
    await db_session.commit()
    await db_session.refresh(prod)
    return prod


@pytest_asyncio.fixture
async def other_product(db_session, category, brand):
    """San pham chi khop 1 loai da de kiem tra filter OR."""
    prod = Product(
        name="Cream Test",
        slug="cream-test",
        description="Kem test",
        price=Decimal("200000"),
        sale_price=None,
        stock=5,
        category_id=category.id,
        brand_id=brand.id,
        skin_types=["combination"],
        concerns=["aging"],
        key_ingredients=None,
        free_from=None,
        variants=None,
        sold_count=0,
        rating_avg=Decimal("0"),
        rating_count=0,
        is_active=True,
    )
    db_session.add(prod)
    await db_session.commit()
    await db_session.refresh(prod)
    return prod
