"""Test unique index DB chan giao dich trung (race condition) + loi domain.

CHECK o tang application (`update_payment_status`) co race condition:
2 request song song (webhook + reconcile) cung 1 giao dich deu doc "khong thay
duplicate" truoc khi ghi => ca 2 don cung `paid` => cong tien 2 lan.

Unique index DB (`uq_orders_transaction_id`) la chot chong cuoi cung. Khi no
chan, service phai nem `DuplicateTransactionError` (de tang API tra 200 cho
SePay, khong phai loi 500 => SePay retry vo ich).
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.model.order import Order
from app.service import order_service
from app.service.order_service import DuplicateTransactionError

ORDER_CODE = "ORD202611071234"


def _make_integrity_error(constraint_name: str = "uq_orders_transaction_id") -> IntegrityError:
    """Tao `IntegrityError` gia nhu unique index DB nem ra."""

    class _Orig(Exception):
        pass

    orig = _Orig()
    orig.constraint_name = constraint_name  # type: ignore[attr-defined]
    return IntegrityError("UPDATE orders ...", {}, orig)


@pytest.fixture
async def order_row(db_session):
    """Tao 1 don sepay thật trong DB test."""
    from app.model.user import User

    user = User(email="dup-tx@example.com", password_hash="x", full_name="Dup")
    db_session.add(user)
    await db_session.flush()

    order = Order(
        user_id=user.id,
        order_code=ORDER_CODE,
        status="pending",
        total=100000,
        payment_method="sepay",
        payment_status="unpaid",
        shipping_name="Test",
        shipping_phone="0901234567",
        shipping_address="123 Duong ABC",
    )
    db_session.add(order)
    await db_session.commit()
    return order


@pytest.mark.asyncio
async def test_duplicate_transaction_raises_domain_error(db_session, order_row):
    """Unique index chan -> nem `DuplicateTransactionError`, khong phai loi chung."""

    async def _raise():
        raise _make_integrity_error()

    db_session.commit = _raise  # type: ignore[method-assign]

    with pytest.raises(DuplicateTransactionError) as exc_info:
        await order_service.update_payment_status(
            db_session,
            order_code=ORDER_CODE,
            transaction_id="SB-DUPLICATE-1",
        )
    assert exc_info.value.transaction_id == "SB-DUPLICATE-1"
    assert exc_info.value.order_code == ORDER_CODE


@pytest.mark.asyncio
async def test_other_integrity_error_is_not_swallowed(db_session, order_row):
    """Loi `IntegrityError` khac (khong phai trung giao dich) -> nem lai nguyên ban."""

    async def _raise():
        raise _make_integrity_error("some_other_constraint")

    db_session.commit = _raise  # type: ignore[method-assign]

    with pytest.raises(IntegrityError):
        await order_service.update_payment_status(
            db_session,
            order_code=ORDER_CODE,
            transaction_id="SB-DUPLICATE-2",
        )


@pytest.mark.asyncio
async def test_real_unique_index_blocks_second_order(db_session, order_row):
    """
    Verify thật ở tầng DB (không mock): unique index trong schema test phải
    chặn việc gán cùng 1 `transaction_id` cho 2 đơn.

    Đây là lớp bảo vệ cuối cùng khi CHECK ở tầng application bị race condition.
    """
    from app.model.user import User

    user = User(email="dup-tx-2@example.com", password_hash="x", full_name="Dup2")
    db_session.add(user)
    await db_session.flush()

    other = Order(
        user_id=user.id,
        order_code="ORD202611075678",
        status="pending",
        total=100000,
        payment_method="sepay",
        payment_status="unpaid",
        shipping_name="Test",
        shipping_phone="0901234567",
        shipping_address="123 Duong ABC",
    )
    db_session.add(other)
    await db_session.commit()

    tx_id = "SB-REAL-UNIQUE-1"
    order_row.transaction_id = tx_id
    order_row.payment_status = "paid"
    await db_session.commit()

    other.transaction_id = tx_id
    other.payment_status = "paid"
    with pytest.raises(IntegrityError) as exc_info:
        await db_session.commit()
    await db_session.rollback()

    assert "uq_orders_transaction_id" in str(exc_info.value)

    rows = (
        await db_session.execute(
            select(Order).where(Order.transaction_id == tx_id)
        )
    ).scalars().all()
    assert len(rows) == 1


def test_is_duplicate_transaction_detects_constraint():
    """Doc loi: nhan dien qua `constraint_name` va fallback qua message."""
    from app.service.order_service import _is_duplicate_transaction

    assert _is_duplicate_transaction(_make_integrity_error()) is True
    assert _is_duplicate_transaction(_make_integrity_error("other")) is False

    class _NoConstraint(Exception):
        pass

    err = IntegrityError("stmt", {}, _NoConstraint())
    err.orig = _NoConstraint("uq_orders_transaction_id violated")  # type: ignore[assignment]
    assert _is_duplicate_transaction(err) is True
