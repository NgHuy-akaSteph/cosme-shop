"""Test khoa chong trung giao dich + schema `id` int/str + check tai khoan nhan tien.

SePay cho 2 nguon ID khac nhau cho cung 1 giao dich that:
- webhook : `id = 44843` (int), `referenceCode = SB2787C335AAF1`
- API v2  : `id = 37dcdb04-d85a-11f1-...` (UUID), `reference_number = SB2787C335AAF1`

=> khoa chong trung phai dung `reference_code` (on dinh giua 2 nguon), neu dung
`id` thi 2 don khac nhau co the cung bi danh paid tu 1 giao dich.
"""

import json

import pytest

from tests.factories import *  # noqa: F401,F403 - nap fixture tu factories

WEBHOOK_URL = "/api/payment/sepay-webhook"
TEST_SECRET = "test-webhook-secret"
REFERENCE_CODE = "SB2787C335AAF1"
UUID_TX_ID = "37dcdb04-d85a-11f1-8895-0afffe87053b"


def build_payload(
    order_code: str,
    amount: int,
    tx_id,
    transfer_type: str = "in",
    account_number: str = "0000000001",
    reference_code: str | None = REFERENCE_CODE,
) -> bytes:
    return json.dumps(
        {
            "id": tx_id,
            "gateway": "VietinBank",
            "transactionDate": "2024-07-02 11:08:33",
            "accountNumber": account_number,
            "subAccount": "",
            "code": order_code,
            "content": f"SEVQR {order_code}",
            "transferType": transfer_type,
            "description": "NGUYEN VAN A chuyen tien",
            "transferAmount": amount,
            "accumulated": 105000000,
            "referenceCode": reference_code,
        }
    ).encode("utf-8")


def signed_headers(raw: bytes, secret: str = TEST_SECRET) -> dict:
    import hashlib
    import hmac
    import time

    ts = int(time.time())
    digest = hmac.new(
        secret.encode("utf-8"),
        f"{ts}.".encode("utf-8") + raw,
        hashlib.sha256,
    ).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-SePay-Signature": f"sha256={digest}",
        "X-SePay-Timestamp": str(ts),
    }


@pytest.fixture(autouse=True)
def _sepay_secret(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "SEPAY_WEBHOOK_SECRET", TEST_SECRET)
    monkeypatch.setattr(settings, "SEPAY_API_KEY", "test-api-key")
    monkeypatch.setattr(settings, "SEPAY_BANK_ACCOUNT", "0000000001")


async def _create_order(client, login, product):
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
    return res.json()["data"]["order"]


# ============================================
# Schema: `id` int (webhook) va UUID (API v2)
# ============================================


def test_payload_schema_accepts_int_and_uuid_id():
    """`id` cua SePay co the la int (webhook) hoac UUID string (API v2)."""
    from app.schemas.payment import SePayWebhookPayload

    base = {"transferType": "in", "transferAmount": 1000, "content": "x"}

    assert SePayWebhookPayload.model_validate({**base, "id": 92704}).transaction_id == "92704"
    assert (
        SePayWebhookPayload.model_validate({**base, "id": UUID_TX_ID}).transaction_id
        == UUID_TX_ID
    )


def test_payload_schema_accepts_string_amounts():
    """SePay co the gui so tien duoi dang chuoi -> phai ep ve int."""
    from app.schemas.payment import SePayWebhookPayload

    payload = SePayWebhookPayload.model_validate(
        {
            "id": 1,
            "transferType": "in",
            "transferAmount": "200000",
            "accumulated": "300000",
            "content": "x",
        }
    )
    assert payload.amount_in == 200000
    assert payload.accumulated == 300000


def test_build_transaction_key_prefers_reference_code():
    """Khoa chong trung dung `reference_code` (on dinh giua 2 nguon)."""
    from app.payment.transaction_key import build_transaction_key

    assert (
        build_transaction_key(reference_code=REFERENCE_CODE, transaction_id=44843)
        == REFERENCE_CODE
    )
    assert (
        build_transaction_key(reference_code=REFERENCE_CODE, transaction_id=UUID_TX_ID)
        == REFERENCE_CODE
    )


def test_build_transaction_key_falls_back_to_id():
    """Khong co `referenceCode` -> fallback sang `id` (int hoac UUID)."""
    from app.payment.transaction_key import build_transaction_key

    assert build_transaction_key(reference_code=None, transaction_id=44843) == "44843"
    assert build_transaction_key(reference_code="", transaction_id=UUID_TX_ID) == UUID_TX_ID


# ============================================
# Webhook: dung khoa reference_code, check tai khoan
# ============================================


@pytest.mark.asyncio
async def test_webhook_stores_reference_code_as_transaction_key(
    client, login, product, db_session
):
    """`orders.transaction_id` = `referenceCode` (khong phai `id` int)."""
    from sqlalchemy import select

    from app.model.order import Order

    order = await _create_order(client, login, product)
    raw = build_payload(order["order_code"], int(float(order["total"])), tx_id=44843)

    res = await client.post(WEBHOOK_URL, content=raw, headers=signed_headers(raw))
    assert res.status_code == 200, res.text

    row = (
        await db_session.execute(select(Order).where(Order.order_code == order["order_code"]))
    ).scalar_one()
    assert row.payment_status == "paid"
    assert row.transaction_id == REFERENCE_CODE


@pytest.mark.asyncio
async def test_webhook_and_reconcile_use_same_key_for_same_transaction(
    client, login, product, db_session, monkeypatch
):
    """
    Cung 1 giao dich, 2 nguon (webhook int id vs API v2 UUID id) => cung 1 khoa.

    Day la ly do phai dung `reference_code` chung khong dung `id`.
    """
    from sqlalchemy import select

    from app.model.order import Order
    from app.service import payment_reconcile_service

    order = await _create_order(client, login, product)
    total = int(float(order["total"]))

    # 1) Webhook voi `id` int -> ghi khoa `referenceCode`
    raw = build_payload(order["order_code"], total, tx_id=44843)
    res = await client.post(WEBHOOK_URL, content=raw, headers=signed_headers(raw))
    assert res.status_code == 200, res.text

    row = (
        await db_session.execute(select(Order).where(Order.order_code == order["order_code"]))
    ).scalar_one()
    assert row.transaction_id == REFERENCE_CODE

    # 2) API v2 cho CUNG giao dich nhung `id` la UUID -> phai ra cung khoa
    from tests.test_payment_reconcile import _FakeClient

    body = {
        "status": "success",
        "data": [
            {
                "id": UUID_TX_ID,
                "transfer_type": "in",
                "code": order["order_code"],
                "transaction_content": f"SEVQR {order['order_code']}",
                "reference_number": REFERENCE_CODE,
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
    res_reconcile = await client.post("/api/payment/reconcile", headers=admin_headers)
    assert res_reconcile.status_code == 200, res_reconcile.text
    # Da paid roi -> khong danh paid lai, transaction_id khong doi.
    assert res_reconcile.json()["data"]["marked_paid"] == 0

    row_after = (
        await db_session.execute(select(Order).where(Order.order_code == order["order_code"]))
    ).scalar_one()
    assert row_after.transaction_id == REFERENCE_CODE


@pytest.mark.asyncio
async def test_webhook_wrong_account_is_not_paid(client, login, product, db_session):
    """Giao dich den tu tai khoan khac -> log `wrong_account`, don van `unpaid`."""
    from sqlalchemy import select

    from app.model.payment_webhook_log import PaymentWebhookLog

    order = await _create_order(client, login, product)
    raw = build_payload(
        order["order_code"],
        int(float(order["total"])),
        tx_id=9901,
        account_number="9999999999",
    )

    res = await client.post(WEBHOOK_URL, content=raw, headers=signed_headers(raw))
    assert res.status_code == 200, res.text
    assert res.json() == {"success": True}

    status_res = await client.get(
        f"/api/payment/status/{order['id']}",
        headers=await login("user@example.com", "user123"),
    )
    assert status_res.json()["data"]["payment_status"] == "unpaid"

    log_row = (
        await db_session.execute(select(PaymentWebhookLog))
    ).scalar_one()
    assert log_row.status == "wrong_account"


@pytest.mark.asyncio
async def test_webhook_account_ignores_leading_zeros(client, login, product):
    """Ngan hang co the gui `1` thay vì `0000000001` -> van phai khop."""
    from app.core.config import settings

    order = await _create_order(client, login, product)
    raw = build_payload(
        order["order_code"],
        int(float(order["total"])),
        tx_id=9902,
        account_number="1",
    )

    res = await client.post(WEBHOOK_URL, content=raw, headers=signed_headers(raw))
    assert res.status_code == 200, res.text

    status_res = await client.get(
        f"/api/payment/status/{order['id']}",
        headers=await login("user@example.com", "user123"),
    )
    assert status_res.json()["data"]["payment_status"] == "paid"


@pytest.mark.asyncio
async def test_webhook_without_reference_code_falls_back_to_id(
    client, login, product, db_session
):
    """Khong co `referenceCode` -> fallback sang `id` (int) de van lai idempotent."""
    from sqlalchemy import select

    from app.model.order import Order

    order = await _create_order(client, login, product)
    raw = build_payload(
        order["order_code"],
        int(float(order["total"])),
        tx_id=44843,
        reference_code=None,
    )

    res = await client.post(WEBHOOK_URL, content=raw, headers=signed_headers(raw))
    assert res.status_code == 200, res.text

    row = (
        await db_session.execute(select(Order).where(Order.order_code == order["order_code"]))
    ).scalar_one()
    assert row.payment_status == "paid"
    assert row.transaction_id == "44843"
