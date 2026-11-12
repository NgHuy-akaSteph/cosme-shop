"""Test thu tu sap xep + tim kiem cho cac danh sach trong trang Admin.

Muc tieu:
- `sort=newest` / `sort=oldest` sap xep theo `created_at` (co tiebreak `id`).
- Khong truyen `sort` -> giu hanh vi cu (alphabet) cho public API.
- `search` loc theo TEN (truong chinh) + truong phu (ma/SĐT/email).
- `total` phai khop so ban ghi tra ve (khong phai tong so ban ghi trong DB).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.model.brand import Brand
from app.model.category import Category
from app.model.order import Order
from app.model.product import Product
from app.model.user import User
from tests.factories import *  # noqa: F401,F403 - nap fixture tu factories

# Moc thoi gian goc de tao `created_at` tang dan tuy tien (khong phu thuoc
# `now()` -> ket qua test on dinh).
BASE_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


async def _make_categories(db_session) -> list[Category]:
    """Tao 3 danh muc theo thu tu tao: Alpha, Beta, Gamma (gia khac nhau)."""
    created = []
    for index, (name, slug) in enumerate(
        [("Alpha", "alpha"), ("Beta", "beta"), ("Gamma", "gamma")]
    ):
        cat = Category(
            name=name,
            slug=slug,
            description=f"Mo ta {name}",
            created_at=BASE_TIME + timedelta(days=index),
            updated_at=BASE_TIME + timedelta(days=index),
        )
        db_session.add(cat)
        created.append(cat)
    await db_session.commit()
    for cat in created:
        await db_session.refresh(cat)
    return created


async def _make_brands(db_session) -> list[Brand]:
    """Tao 3 thuong hieu theo thu tu tao: Alpha, Beta, Gamma."""
    created = []
    for index, (name, slug) in enumerate(
        [("Alpha", "alpha"), ("Beta", "beta"), ("Gamma", "gamma")]
    ):
        brand = Brand(
            name=name,
            slug=slug,
            description=f"Mo ta {name}",
            created_at=BASE_TIME + timedelta(days=index),
            updated_at=BASE_TIME + timedelta(days=index),
        )
        db_session.add(brand)
        created.append(brand)
    await db_session.commit()
    for brand in created:
        await db_session.refresh(brand)
    return created


async def _make_products(
    db_session, category: Category, brand: Brand
) -> list[Product]:
    """Tao 3 san pham cung gia (de kiem tra tiebreak id)."""
    created = []
    for index, name in enumerate(["Alpha", "Beta", "Gamma"]):
        product = Product(
            name=name,
            slug=f"alpha-beta-gamma-{index}",
            description=f"Mo ta {name}",
            price=Decimal("100000"),
            sale_price=None,
            stock=10,
            category_id=category.id,
            brand_id=brand.id,
            skin_types=None,
            concerns=None,
            key_ingredients=None,
            free_from=None,
            variants=None,
            sold_count=0,
            rating_avg=Decimal("0"),
            rating_count=0,
            is_active=True,
            created_at=BASE_TIME + timedelta(days=index),
            updated_at=BASE_TIME + timedelta(days=index),
        )
        db_session.add(product)
        created.append(product)
    await db_session.commit()
    for product in created:
        await db_session.refresh(product)
    return created


# ---------------------------------------------------------------- sort


@pytest.mark.asyncio
async def test_categories_sort_newest_returns_newest_first(client, db_session):
    """`sort=newest` -> ban ghi tao sau cung truoc."""
    await _make_categories(db_session)

    res = await client.get("/api/categories?sort=newest")
    assert res.status_code == 200, res.text

    names = [c["name"] for c in res.json()["data"]]
    assert names == ["Gamma", "Beta", "Alpha"]


@pytest.mark.asyncio
async def test_categories_sort_oldest_returns_oldest_first(client, db_session):
    await _make_categories(db_session)

    res = await client.get("/api/categories?sort=oldest")
    assert res.status_code == 200, res.text

    names = [c["name"] for c in res.json()["data"]]
    assert names == ["Alpha", "Beta", "Gamma"]


@pytest.mark.asyncio
async def test_categories_default_sort_stays_alphabetical(client, db_session):
    """Khong truyen `sort` -> giu hanh vi public API cu (alphabet theo ten)."""
    await _make_categories(db_session)

    res = await client.get("/api/categories")
    assert res.status_code == 200, res.text

    names = [c["name"] for c in res.json()["data"]]
    assert names == ["Alpha", "Beta", "Gamma"]


@pytest.mark.asyncio
async def test_brands_sort_newest_returns_newest_first(client, db_session):
    await _make_brands(db_session)

    res = await client.get("/api/brands?sort=newest")
    assert res.status_code == 200, res.text

    names = [b["name"] for b in res.json()["data"]]
    assert names == ["Gamma", "Beta", "Alpha"]


@pytest.mark.asyncio
async def test_brands_default_sort_stays_alphabetical(client, db_session):
    await _make_brands(db_session)

    res = await client.get("/api/brands")
    names = [b["name"] for b in res.json()["data"]]
    assert names == ["Alpha", "Beta", "Gamma"]


@pytest.mark.asyncio
async def test_products_sort_newest_returns_newest_first(client, db_session):
    categories = await _make_categories(db_session)
    brands = await _make_brands(db_session)
    await _make_products(db_session, categories[0], brands[0])

    res = await client.get("/api/products?sort=newest")
    assert res.status_code == 200, res.text

    names = [p["name"] for p in res.json()["data"]]
    assert names == ["Gamma", "Beta", "Alpha"]


@pytest.mark.asyncio
async def test_products_price_asc_has_id_tiebreak(client, db_session):
    """3 san pham cung gia -> thu tu theo `id` giam dan (phan trang on dinh)."""
    categories = await _make_categories(db_session)
    brands = await _make_brands(db_session)
    products = await _make_products(db_session, categories[0], brands[0])

    res = await client.get("/api/products?sort=price_asc")
    assert res.status_code == 200, res.text

    ids = [p["id"] for p in res.json()["data"]]
    expected = [p.id for p in reversed(products)]
    assert ids == expected


@pytest.mark.asyncio
async def test_products_default_sort_keeps_id_desc(client, db_session):
    """Khong truyen `sort` -> giu hanh vi public cu (id giam dan)."""
    categories = await _make_categories(db_session)
    brands = await _make_brands(db_session)
    products = await _make_products(db_session, categories[0], brands[0])

    res = await client.get("/api/products")
    assert res.status_code == 200, res.text

    ids = [p["id"] for p in res.json()["data"]]
    assert ids == [p.id for p in reversed(products)]


# -------------------------------------------------------------- search


@pytest.mark.asyncio
async def test_search_products_by_name(client, db_session):
    categories = await _make_categories(db_session)
    brands = await _make_brands(db_session)
    await _make_products(db_session, categories[0], brands[0])

    res = await client.get("/api/products?search=Beta")
    assert res.status_code == 200, res.text

    body = res.json()
    assert [p["name"] for p in body["data"]] == ["Beta"]
    assert body["total"] == 1


@pytest.mark.asyncio
async def test_search_products_no_match_returns_empty(client, db_session):
    categories = await _make_categories(db_session)
    brands = await _make_brands(db_session)
    await _make_products(db_session, categories[0], brands[0])

    res = await client.get("/api/products?search=khongcothat")
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["data"] == []
    # `total` phai la 0, KHONG phai tong so san pham trong DB.
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_search_users_by_name(client, login, db_session, admin_user):
    """Tim theo TEN (truong chinh) - chi tra ve user khop ten."""
    headers = await login("admin@example.com", "admin123")

    users = [
        User(
            email=f"user{index}@example.com",
            password_hash=admin_user.password_hash,
            full_name=name,
            phone=f"090000000{index}",
            role="user",
            is_active=True,
            created_at=BASE_TIME + timedelta(days=index),
            updated_at=BASE_TIME + timedelta(days=index),
        )
        for index, name in enumerate(["Nguyen Van A", "Tran Thi B", "Le Van C"])
    ]
    db_session.add_all(users)
    await db_session.commit()

    res = await client.get("/api/admin/users?search=Tran", headers=headers)
    assert res.status_code == 200, res.text

    body = res.json()
    assert [u["full_name"] for u in body["data"]] == ["Tran Thi B"]
    assert body["total"] == 1


@pytest.mark.asyncio
async def test_search_users_by_email_secondary_field(client, login, db_session, admin_user):
    """Email la truong phu -> van tim ra duoc."""
    headers = await login("admin@example.com", "admin123")

    user = User(
        email="nguyenvana@example.com",
        password_hash=admin_user.password_hash,
        full_name="Nguyen Van A",
        phone="0900000000",
        role="user",
        is_active=True,
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )
    db_session.add(user)
    await db_session.commit()

    res = await client.get("/api/admin/users?search=nguyenvana@", headers=headers)
    assert res.status_code == 200, res.text

    body = res.json()
    assert [u["full_name"] for u in body["data"]] == ["Nguyen Van A"]
    assert body["total"] == 1


@pytest.mark.asyncio
async def test_search_users_no_match_total_is_zero(client, login, db_session, admin_user):
    """Khong co ket qua -> `total` = 0 (khong phai tong so user trong DB)."""
    headers = await login("admin@example.com", "admin123")

    user = User(
        email="nguyenvana@example.com",
        password_hash=admin_user.password_hash,
        full_name="Nguyen Van A",
        phone="0900000000",
        role="user",
        is_active=True,
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )
    db_session.add(user)
    await db_session.commit()

    res = await client.get("/api/admin/users?search=khongcothat", headers=headers)
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["data"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_search_orders_by_order_code(client, login, db_session, normal_user):
    """Tim don hang theo MA DON."""
    headers = await login("admin@example.com", "admin123")

    order = Order(
        user_id=normal_user.id,
        order_code="ORD-TEST-0001",
        status="pending",
        subtotal=Decimal("100000"),
        discount_code=None,
        discount_amount=Decimal("0"),
        total=Decimal("100000"),
        payment_method="cod",
        payment_status="unpaid",
        shipping_name="Nguyen Van A",
        shipping_phone="0901234567",
        shipping_address="123 Duong ABC",
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )
    db_session.add(order)
    await db_session.commit()

    res = await client.get("/api/admin/orders?search=ORD-TEST-0001", headers=headers)
    assert res.status_code == 200, res.text

    body = res.json()
    assert [o["order_code"] for o in body["data"]] == ["ORD-TEST-0001"]
    assert body["total"] == 1


@pytest.mark.asyncio
async def test_search_orders_partial_code_matches(client, login, db_session, normal_user):
    """Ma don la chuoi -> tim theo mot phan van ra ket qua."""
    headers = await login("admin@example.com", "admin123")

    order = Order(
        user_id=normal_user.id,
        order_code="ORD-TEST-0002",
        status="pending",
        subtotal=Decimal("100000"),
        discount_code=None,
        discount_amount=Decimal("0"),
        total=Decimal("100000"),
        payment_method="cod",
        payment_status="unpaid",
        shipping_name="Tran Thi B",
        shipping_phone="0901234567",
        shipping_address="123 Duong ABC",
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )
    db_session.add(order)
    await db_session.commit()

    res = await client.get("/api/admin/orders?search=TEST-0002", headers=headers)
    assert res.status_code == 200, res.text

    body = res.json()
    assert [o["order_code"] for o in body["data"]] == ["ORD-TEST-0002"]
    assert body["total"] == 1


@pytest.mark.asyncio
async def test_search_orders_ignores_customer_name(client, login, db_session, normal_user):
    """Chi loc theo MA DON -> ten khach khong con la dieu kien loc."""
    headers = await login("admin@example.com", "admin123")

    order = Order(
        user_id=normal_user.id,
        order_code="ORD-TEST-0003",
        status="pending",
        subtotal=Decimal("100000"),
        discount_code=None,
        discount_amount=Decimal("0"),
        total=Decimal("100000"),
        payment_method="cod",
        payment_status="unpaid",
        shipping_name="Le Van C",
        shipping_phone="0901234567",
        shipping_address="123 Duong ABC",
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )
    db_session.add(order)
    await db_session.commit()

    res = await client.get("/api/admin/orders?search=Le Van C", headers=headers)
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["data"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_search_orders_no_match_total_is_zero(client, login, db_session, normal_user):
    headers = await login("admin@example.com", "admin123")

    order = Order(
        user_id=normal_user.id,
        order_code="ORD-TEST-0004",
        status="pending",
        subtotal=Decimal("100000"),
        discount_code=None,
        discount_amount=Decimal("0"),
        total=Decimal("100000"),
        payment_method="cod",
        payment_status="unpaid",
        shipping_name="Nguyen Van A",
        shipping_phone="0901234567",
        shipping_address="123 Duong ABC",
        created_at=BASE_TIME,
        updated_at=BASE_TIME,
    )
    db_session.add(order)
    await db_session.commit()

    res = await client.get("/api/admin/orders?search=khongcothat", headers=headers)
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["data"] == []
    assert body["total"] == 0
