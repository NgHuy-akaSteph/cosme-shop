"""Test dinh dang "ma thanh toan" (order_code) khop voi mau ma SePay.

SePay boc tach `code` tu noi dung CK theo mau ma khai bao tren dashboard. Sai
dinh dang => SePay bo qua giao dich => mat tien, don ket `unpaid`.
"""

import re

from tests.factories import *  # noqa: F401,F403 - nap fixture tu factories


def _settings(monkeypatch, prefix="ORD", suffix_length=12):
    from app.core.config import settings

    monkeypatch.setattr(settings, "SEPAY_PAYMENT_CODE_PREFIX", prefix)
    monkeypatch.setattr(settings, "SEPAY_PAYMENT_CODE_SUFFIX_LENGTH", suffix_length)


def test_generate_order_code_matches_sepay_pattern(monkeypatch):
    """Ma don phai khop `^{prefix}\\d{suffix_len}$` - dinh dang SePay trich ra."""
    from app.service.order_service import generate_order_code

    _settings(monkeypatch)
    code = generate_order_code()
    assert re.fullmatch(r"ORD\d{12}", code), code


def test_generate_order_code_respects_config(monkeypatch):
    """Doi prefix / do dai hau to trong config => ma doi theo (1 nguon su that)."""
    from app.service.order_service import generate_order_code

    _settings(monkeypatch, prefix="SHOP", suffix_length=10)
    code = generate_order_code()
    assert re.fullmatch(r"SHOP\d{10}", code), code


def test_generate_order_code_prefix_validated(monkeypatch):
    """Tien to ngoai 2-5 ky tu (quy dinh SePay) => nem loi, khong sinh ma sai."""
    import pytest

    from app.service.order_service import generate_order_code

    _settings(monkeypatch, prefix="O")
    with pytest.raises(ValueError):
        generate_order_code()


def test_generate_order_code_length_within_column_limit(monkeypatch):
    """Ma qua dai => khong duoc ghi vao `orders.order_code` (String(32))."""
    import pytest

    from app.service.order_service import generate_order_code

    _settings(monkeypatch, prefix="ORD", suffix_length=30)
    with pytest.raises(ValueError):
        generate_order_code()


def test_validate_payment_code_raises_on_mismatch(monkeypatch):
    """Ma sai dinh dang => fail-fast (khong sinh QR sai = khong mat tien)."""
    import pytest

    from app.payment.payment_code import validate_payment_code

    _settings(monkeypatch)
    assert validate_payment_code("ORD202611042239") == "ORD202611042239"

    with pytest.raises(ValueError):
        validate_payment_code("COSME6246552")
    with pytest.raises(ValueError):
        validate_payment_code("ORD20261104223")  # thieu 1 chu so
    with pytest.raises(ValueError):
        validate_payment_code("ORD2026110422399")  # thua 1 chu so


def test_payment_code_pattern_extracts_from_content(monkeypatch):
    """Regex trich ma tu `content` noi dung CK (co prefix ngan hang `SEVQR`)."""
    from app.payment.payment_code import payment_code_pattern

    _settings(monkeypatch)
    pattern = payment_code_pattern()

    assert pattern.search("SEVQR ORD202611042239").group(0) == "ORD202611042239"
    assert pattern.search("ORD202611042239 chuyen tien").group(0) == "ORD202611042239"
    # Cat nganh ma khi noi dung co them chu so phia sau (SePay cung cat theo mau).
    assert pattern.search("ORD202611042239999").group(0) == "ORD202611042239"
    # Ma cu (mau "COSME") khong duoc match => giao dich la cu nguoi khac.
    assert pattern.search("COSME6246552") is None


def test_extract_order_code_uses_dynamic_prefix(monkeypatch):
    """Doi prefix trong config => provider trich ma theo prefix moi."""
    from app.payment.sepay_provider import SePayProvider

    _settings(monkeypatch, prefix="SHOP", suffix_length=10)

    class FakePayload:
        code = "SHOP1234567890"
        sub_account = ""
        content = "SEVQR SHOP1234567890"

    assert SePayProvider().extract_order_code(FakePayload()) == "SHOP1234567890"


def test_create_payment_link_rejects_invalid_order_code(monkeypatch):
    """`create_payment_link` nem loi khi ma khong khop mau SePay (fail-fast)."""
    import pytest
    from decimal import Decimal

    from app.core.config import settings
    from app.payment.sepay_provider import SePayProvider

    _settings(monkeypatch)
    monkeypatch.setattr(settings, "SEPAY_BANK_ACCOUNT", "0000000001")
    monkeypatch.setattr(settings, "SEPAY_BANK_NAME", "ICB")
    monkeypatch.setattr(settings, "SEPAY_QR_CONTENT_PREFIX", "SEVQR")

    class FakeOrder:
        total = Decimal("430000.0")
        order_code = "COSME6246552"

    with pytest.raises(ValueError):
        SePayProvider().create_payment_link(FakeOrder())
