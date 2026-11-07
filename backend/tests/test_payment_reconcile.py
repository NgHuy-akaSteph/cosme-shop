"""Test doi soat thanh toan: cua so ngay (exclusive) + phan trang.

SePay API v2 coi `transaction_date_to` là EXCLUSIVE: giao dich trong chinh ngay
`to` KHONG duoc tra ve. Code cu quet `from = today - days`, `to = today` =>
cua so rong => `scanned = 0` => lop an toan thu hai (doi soat) khong bao gio
chay duoc.
"""

import datetime as dt

import pytest

from tests.factories import *  # noqa: F401,F403 - nap fixture tu factories


class _FakeResponse:
    def __init__(self, body: dict):
        self._body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self._body


class _FakeClient:
    """Ghi lai params de assert, tra payload gia lap."""

    def __init__(self, body: dict):
        self._body = body
        self.calls: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, params=None, headers=None):
        self.calls.append(dict(params or {}))
        return _FakeResponse(self._body)


@pytest.fixture
def _capture_client(monkeypatch):
    """Patch `httpx.AsyncClient` trong module doi soat, trả về fake client."""
    from app.service import payment_reconcile_service

    fake = _FakeClient(
        {
            "status": "success",
            "data": [],
            "meta": {"pagination": {"has_more": False, "total": 0}},
        }
    )

    def _factory(*args, **kwargs):
        return fake

    monkeypatch.setattr(payment_reconcile_service.httpx, "AsyncClient", _factory)
    monkeypatch.setattr(payment_reconcile_service.settings, "SEPAY_API_TOKEN", "token")
    return fake


@pytest.mark.asyncio
async def test_date_window_excludes_today_without_plus_one(_capture_client):
    """
    `transaction_date_to` phai = hom nay + 1 ngay.

    SePay API v2 coi `transaction_date_to` là exclusive. Neu de `to = today`
    thi giao dich hom nay bi lo (va `from == to` => rong).
    """
    from app.service.payment_reconcile_service import fetch_recent_transactions

    await fetch_recent_transactions(days=3)

    params = _capture_client.calls[0]
    today = dt.datetime.now(dt.timezone.utc).date()

    assert params["transaction_date_to"] == (today + dt.timedelta(days=1)).isoformat()
    assert params["transaction_date_from"] == (today - dt.timedelta(days=3)).isoformat()
    # Khong duoc de from == to (cua so rong).
    assert params["transaction_date_from"] < params["transaction_date_to"]


@pytest.mark.asyncio
async def test_date_window_zero_days_still_returns_today(_capture_client):
    """`days=0` van phai quet duoc giao dich hom nay (from < to)."""
    from app.service.payment_reconcile_service import fetch_recent_transactions

    await fetch_recent_transactions(days=0)

    params = _capture_client.calls[0]
    today = dt.datetime.now(dt.timezone.utc).date()
    assert params["transaction_date_from"] == today.isoformat()
    assert params["transaction_date_to"] == (today + dt.timedelta(days=1)).isoformat()


@pytest.mark.asyncio
async def test_fetch_paginates_and_filters_transfer_type(monkeypatch):
    """Phan trang + chi giu giao dich tien vao."""
    from app.service import payment_reconcile_service

    pages = [
        {
            "status": "success",
            "data": [
                {"id": "t1", "transfer_type": "in", "code": "ORD202611042239"},
                {"id": "t2", "transfer_type": "out", "code": "ORD202611042240"},
            ],
            "meta": {"pagination": {"has_more": True}},
        },
        {
            "status": "success",
            "data": [{"id": "t3", "transfer_type": "in", "code": "ORD202611042241"}],
            "meta": {"pagination": {"has_more": False}},
        },
    ]

    calls: list[dict] = []

    class _PagedClient(_FakeClient):
        async def get(self, url, params=None, headers=None):
            calls.append(dict(params or {}))
            body = pages[len(calls) - 1]
            return _FakeResponse(body)

    fake = _PagedClient({})
    monkeypatch.setattr(payment_reconcile_service.httpx, "AsyncClient", lambda *a, **k: fake)
    monkeypatch.setattr(payment_reconcile_service.settings, "SEPAY_API_TOKEN", "token")

    txs = await payment_reconcile_service.fetch_recent_transactions(days=3)

    assert len(calls) == 2
    assert calls[0]["page"] == 1
    assert calls[1]["page"] == 2
    assert [tx["id"] for tx in txs] == ["t1", "t3"]


@pytest.mark.asyncio
async def test_reconcile_marks_paid_and_is_idempotent(monkeypatch, client, login, product):
    """Don `unpaid` khop ma => paid; chay lai lan 2 => khong doi trang thai."""
    from sqlalchemy import select

    from app.model.order import Order
    from app.service import payment_reconcile_service

    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/orders",
        json={
            "items": [{"product_id": product.id, "qty": 1}],
            "shipping_name": "Nguyen Van A",
            "shipping_phone": "0901234567",
            "shipping_address": "123 Duong ABC, Quan 1, TP.HCM",
            "payment_method": "sepay",
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    order_code = res.json()["data"]["order"]["order_code"]

    total = int(float(res.json()["data"]["order"]["total"]))
    body = {
        "status": "success",
        "data": [
            {
                "id": "tx-reconcile-1",
                "transfer_type": "in",
                "code": order_code,
                "transaction_content": f"SEVQR {order_code}",
                "amount_in": total,
            }
        ],
        "meta": {"pagination": {"has_more": False}},
    }
    monkeypatch.setattr(
        payment_reconcile_service.httpx,
        "AsyncClient",
        lambda *a, **k: _FakeClient(body),
    )
    monkeypatch.setattr(payment_reconcile_service.settings, "SEPAY_API_TOKEN", "token")

    admin_headers = await login("admin@example.com", "admin123")

    first = await client.post("/api/payment/reconcile", headers=admin_headers)
    assert first.status_code == 200, first.text
    stats = first.json()["data"]
    assert stats["scanned"] == 1
    assert stats["marked_paid"] == 1

    status_res = await client.get(
        f"/api/payment/status/{res.json()['data']['order']['id']}", headers=headers
    )
    assert status_res.json()["data"]["payment_status"] == "paid"

    # Lan 2: don da paid -> khong con trong danh sach unpaid => khong doi lai.
    second = await client.post("/api/payment/reconcile", headers=admin_headers)
    assert second.status_code == 200, second.text
    assert second.json()["data"]["marked_paid"] == 0


@pytest.mark.asyncio
async def test_reconcile_skips_order_with_insufficient_amount(monkeypatch, client, login, product):
    """Giao dich thieu tien => KHONG danh paid, `skipped` tang."""
    from app.service import payment_reconcile_service

    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/orders",
        json={
            "items": [{"product_id": product.id, "qty": 1}],
            "shipping_name": "Nguyen Van A",
            "shipping_phone": "0901234567",
            "shipping_address": "123 Duong ABC, Quan 1, TP.HCM",
            "payment_method": "sepay",
        },
        headers=headers,
    )
    order_code = res.json()["data"]["order"]["order_code"]
    total = int(float(res.json()["data"]["order"]["total"]))

    body = {
        "status": "success",
        "data": [
            {
                "id": "tx-reconcile-short",
                "transfer_type": "in",
                "code": order_code,
                "transaction_content": f"SEVQR {order_code}",
                "amount_in": total - 1000,
            }
        ],
        "meta": {"pagination": {"has_more": False}},
    }
    monkeypatch.setattr(
        payment_reconcile_service.httpx,
        "AsyncClient",
        lambda *a, **k: _FakeClient(body),
    )
    monkeypatch.setattr(payment_reconcile_service.settings, "SEPAY_API_TOKEN", "token")

    admin_headers = await login("admin@example.com", "admin123")
    res_reconcile = await client.post("/api/payment/reconcile", headers=admin_headers)
    stats = res_reconcile.json()["data"]
    assert stats["skipped"] == 1
    assert stats["marked_paid"] == 0

    status_res = await client.get(
        f"/api/payment/status/{res.json()['data']['order']['id']}", headers=headers
    )
    assert status_res.json()["data"]["payment_status"] == "unpaid"


@pytest.mark.asyncio
async def test_reconcile_returns_empty_stats_when_api_has_no_data(_capture_client):
    """API tra 0 giao dich => stats 0, khong crash."""
    from app.service.payment_reconcile_service import reconcile_pending_orders

    class _FakeDb:
        async def execute(self, *args, **kwargs):
            class _Result:
                def scalars(self):
                    return self

                def all(self):
                    return []

            return _Result()

    stats = await reconcile_pending_orders(_FakeDb())
    assert stats == {"scanned": 0, "matched": 0, "marked_paid": 0, "skipped": 0}
