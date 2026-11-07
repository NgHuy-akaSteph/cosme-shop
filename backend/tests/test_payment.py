"""Test webhook SePay: xac thuc, idempotent, amount mismatch, don da huy."""

import hashlib
import hmac
import json
import time

import pytest

from tests.factories import *  # noqa: F401,F403 - nap fixture tu factories

WEBHOOK_URL = "/api/payment/sepay-webhook"
TEST_SECRET = "test-webhook-secret"


def build_payload(order_code: str, amount: int, tx_id: int, transfer_type: str = "in") -> bytes:
    return json.dumps(
        {
            "id": tx_id,
            "gateway": "Vietcombank",
            "transactionDate": "2024-07-02 11:08:33",
            "accountNumber": "1017588888",
            "subAccount": "",
            "code": order_code,
            "content": f"{order_code} chuyen tien",
            "transferType": transfer_type,
            "description": "NGUYEN VAN A chuyen tien",
            "transferAmount": amount,
            "accumulated": 105000000,
            "referenceCode": "FT24012345678",
        }
    ).encode("utf-8")


def signed_headers(raw: bytes, secret: str = TEST_SECRET) -> dict:
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
    """Bật HMAC-SHA256 cho toan bộ module test."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "SEPAY_WEBHOOK_SECRET", TEST_SECRET)
    monkeypatch.setattr(settings, "SEPAY_API_KEY", "test-api-key")
    # Khớp `accountNumber` trong payload giả (check tài khoản nhận tiền).
    monkeypatch.setattr(settings, "SEPAY_BANK_ACCOUNT", "1017588888")


async def _create_order(client, login, product, method="sepay"):
    headers = await login("user@example.com", "user123")
    res = await client.post(
        "/api/orders",
        json={
            "items": [{"product_id": product.id, "qty": 1}],
            "shipping_name": "Nguyen Van A",
            "shipping_phone": "0901234567",
            "shipping_address": "123 Duong ABC, Quan 1, TP.HCM",
            "payment_method": method,
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["data"]["order"]


@pytest.mark.asyncio
async def test_webhook_valid_payload_marks_paid(client, login, product):
    order = await _create_order(client, login, product)
    raw = build_payload(order["order_code"], int(float(order["total"])), tx_id=9001)

    res = await client.post(WEBHOOK_URL, content=raw, headers=signed_headers(raw))
    assert res.status_code == 200, res.text
    assert res.json() == {"success": True}

    status_res = await client.get(
        f"/api/payment/status/{order['id']}",
        headers=await login("user@example.com", "user123"),
    )
    assert status_res.status_code == 200
    assert status_res.json()["data"]["payment_status"] == "paid"


@pytest.mark.asyncio
async def test_webhook_invalid_signature_401(client, login, product):
    order = await _create_order(client, login, product)
    raw = build_payload(order["order_code"], int(float(order["total"])), tx_id=9002)

    headers = signed_headers(raw)
    headers["X-SePay-Signature"] = "sha256=deadbeef"

    res = await client.post(WEBHOOK_URL, content=raw, headers=headers)
    assert res.status_code == 401, res.text


@pytest.mark.asyncio
async def test_webhook_expired_timestamp_401(client, login, product):
    order = await _create_order(client, login, product)
    raw = build_payload(order["order_code"], int(float(order["total"])), tx_id=9003)

    old_ts = int(time.time()) - 1000
    digest = hmac.new(
        TEST_SECRET.encode("utf-8"),
        f"{old_ts}.".encode("utf-8") + raw,
        hashlib.sha256,
    ).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-SePay-Signature": f"sha256={digest}",
        "X-SePay-Timestamp": str(old_ts),
    }

    res = await client.post(WEBHOOK_URL, content=raw, headers=headers)
    assert res.status_code == 401, res.text


@pytest.mark.asyncio
async def test_webhook_outgoing_transfer_ignored(client, login, product):
    order = await _create_order(client, login, product)
    raw = build_payload(
        order["order_code"], int(float(order["total"])), tx_id=9004, transfer_type="out"
    )

    res = await client.post(WEBHOOK_URL, content=raw, headers=signed_headers(raw))
    assert res.status_code == 200, res.text

    status_res = await client.get(
        f"/api/payment/status/{order['id']}",
        headers=await login("user@example.com", "user123"),
    )
    assert status_res.json()["data"]["payment_status"] == "unpaid"


@pytest.mark.asyncio
async def test_webhook_amount_short_keeps_unpaid(client, login, product):
    order = await _create_order(client, login, product)
    short_amount = int(float(order["total"])) - 1000
    raw = build_payload(order["order_code"], short_amount, tx_id=9005)

    res = await client.post(WEBHOOK_URL, content=raw, headers=signed_headers(raw))
    assert res.status_code == 200, res.text

    status_res = await client.get(
        f"/api/payment/status/{order['id']}",
        headers=await login("user@example.com", "user123"),
    )
    assert status_res.json()["data"]["payment_status"] == "unpaid"


@pytest.mark.asyncio
async def test_webhook_is_idempotent(client, login, product, db_session):
    from sqlalchemy import func, select

    from app.model.payment_webhook_log import PaymentWebhookLog

    order = await _create_order(client, login, product)
    raw = build_payload(order["order_code"], int(float(order["total"])), tx_id=9006)

    for _ in range(3):
        res = await client.post(WEBHOOK_URL, content=raw, headers=signed_headers(raw))
        assert res.status_code == 200, res.text

    count = (
        await db_session.execute(select(func.count(PaymentWebhookLog.id)))
    ).scalar_one()
    assert count == 1

    log_row = (
        await db_session.execute(select(PaymentWebhookLog))
    ).scalar_one()
    assert log_row.status == "processed"


@pytest.mark.asyncio
async def test_webhook_cancelled_order_not_paid(client, login, product):
    order = await _create_order(client, login, product)

    user_headers = await login("user@example.com", "user123")
    cancel_res = await client.post(
        f"/api/orders/{order['id']}/cancel", headers=user_headers
    )
    assert cancel_res.status_code == 200, cancel_res.text

    raw = build_payload(order["order_code"], int(float(order["total"])), tx_id=9007)
    res = await client.post(WEBHOOK_URL, content=raw, headers=signed_headers(raw))
    assert res.status_code == 200, res.text

    status_res = await client.get(
        f"/api/payment/status/{order['id']}", headers=user_headers
    )
    assert status_res.json()["data"]["payment_status"] == "unpaid"


@pytest.mark.asyncio
async def test_webhook_unmatched_order_code(client, login, product):
    raw = build_payload("ORD9999999999", 100000, tx_id=9008)
    res = await client.post(WEBHOOK_URL, content=raw, headers=signed_headers(raw))
    assert res.status_code == 200, res.text
    assert res.json() == {"success": True}


@pytest.mark.asyncio
async def test_payment_status_requires_auth(client, login, product):
    order = await _create_order(client, login, product)

    res = await client.get(f"/api/payment/status/{order['id']}")
    assert res.status_code == 401, res.text


@pytest.mark.asyncio
async def test_payment_status_forbidden_other_user(client, login, product):
    order = await _create_order(client, login, product)

    other = await login("admin@example.com", "admin123")
    res = await client.get(f"/api/payment/status/{order['id']}", headers=other)
    # Admin duoc xem moi don cua user khac
    assert res.status_code == 200, res.text


@pytest.mark.asyncio
async def test_reconcile_requires_admin(client, login):
    res = await client.post("/api/payment/reconcile")
    assert res.status_code == 401, res.text

    user_headers = await login("user@example.com", "user123")
    res = await client.post("/api/payment/reconcile", headers=user_headers)
    assert res.status_code == 403, res.text

    admin_headers = await login("admin@example.com", "admin123")
    res = await client.post("/api/payment/reconcile", headers=admin_headers)
    assert res.status_code == 200, res.text
    assert "scanned" in res.json()["data"]


# ============================================
# QR VietQR: format so tien + noi dung chuyen khoan
# ============================================


def test_format_vnd_amount_strips_decimal_and_exponent():
    """`amount` phai la so nguyen VND, khong phai Decimal float/exponent."""
    from decimal import Decimal

    from app.payment.sepay_provider import format_vnd_amount

    assert format_vnd_amount(Decimal("430000.0")) == "430000"
    assert format_vnd_amount(Decimal("1.00E+6")) == "1000000"
    assert format_vnd_amount(Decimal("1234500")) == "1234500"
    assert format_vnd_amount(430000.0) == "430000"


def test_qr_url_amount_is_plain_integer(monkeypatch):
    """Total doc tu DB co the la Decimal -> QR amount phai la int thuan."""
    from decimal import Decimal

    from app.core.config import settings
    from app.payment.sepay_provider import SePayProvider

    monkeypatch.setattr(settings, "SEPAY_BANK_ACCOUNT", "0000000001")
    monkeypatch.setattr(settings, "SEPAY_BANK_NAME", "ICB")
    monkeypatch.setattr(settings, "SEPAY_QR_CONTENT_PREFIX", "")

    class FakeOrder:
        total = Decimal("430000.0")
        order_code = "ORD202611040001"

    qr_url = SePayProvider().create_payment_link(FakeOrder()).qr_url
    assert qr_url is not None
    assert "amount=430000&" in qr_url
    assert "amount=430000.0" not in qr_url
    assert "des=ORD202611040001" in qr_url


def test_qr_content_prefix_sevqr_for_vietinbank(monkeypatch):
    """VietinBank ca nhan bat buoc 'SEVQR' trong noi dung chuyen khoan."""
    from decimal import Decimal

    from app.core.config import settings
    from app.payment.sepay_provider import SePayProvider

    monkeypatch.setattr(settings, "SEPAY_BANK_ACCOUNT", "0000000001")
    monkeypatch.setattr(settings, "SEPAY_BANK_NAME", "ICB")
    monkeypatch.setattr(settings, "SEPAY_QR_CONTENT_PREFIX", "SEVQR")
    monkeypatch.setattr(settings, "SEPAY_PAYMENT_CODE_PREFIX", "ORD")
    monkeypatch.setattr(settings, "SEPAY_PAYMENT_CODE_SUFFIX_LENGTH", 12)

    class FakeOrder:
        total = Decimal("430000.0")
        order_code = "ORD202611040001"

    qr_url = SePayProvider().create_payment_link(FakeOrder()).qr_url
    assert qr_url is not None
    assert "des=SEVQR%20ORD202611040001" in qr_url


def test_qr_content_without_bank_prefix(monkeypatch):
    """Ngan hang khong yeu cau tien to -> `des` chi chua ma thanh toan."""
    from decimal import Decimal

    from app.core.config import settings
    from app.payment.sepay_provider import SePayProvider

    monkeypatch.setattr(settings, "SEPAY_BANK_ACCOUNT", "0000000001")
    monkeypatch.setattr(settings, "SEPAY_BANK_NAME", "ICB")
    monkeypatch.setattr(settings, "SEPAY_QR_CONTENT_PREFIX", "")
    monkeypatch.setattr(settings, "SEPAY_PAYMENT_CODE_PREFIX", "ORD")
    monkeypatch.setattr(settings, "SEPAY_PAYMENT_CODE_SUFFIX_LENGTH", 12)

    class FakeOrder:
        total = Decimal("430000.0")
        order_code = "ORD202611040001"

    qr_url = SePayProvider().create_payment_link(FakeOrder()).qr_url
    assert qr_url is not None
    assert "des=ORD202611040001" in qr_url
