"""Test kiem tra cau hinh thanh toan luc khoi dong app (fail-fast)."""

import pytest

from app.core.config import settings
from app.payment.payment_config_check import check_payment_config


@pytest.fixture(autouse=True)
def _valid_config(monkeypatch):
    """Cau hinh hop le mac dinh cho moi test."""
    monkeypatch.setattr(settings, "SEPAY_PAYMENT_CODE_PREFIX", "ORD")
    monkeypatch.setattr(settings, "SEPAY_PAYMENT_CODE_SUFFIX_LENGTH", 12)
    monkeypatch.setattr(settings, "SEPAY_QR_CONTENT_PREFIX", "SEVQR")
    monkeypatch.setattr(settings, "SEPAY_BANK_NAME", "ICB")
    monkeypatch.setattr(settings, "SEPAY_BANK_ACCOUNT", "0000000001")
    monkeypatch.setattr(settings, "SEPAY_WEBHOOK_SECRET", "secret")
    monkeypatch.setattr(settings, "SEPAY_API_TOKEN", "token")


def test_valid_config_passes():
    assert check_payment_config() == []


def test_prefix_too_short_raises(monkeypatch):
    monkeypatch.setattr(settings, "SEPAY_PAYMENT_CODE_PREFIX", "O")
    with pytest.raises(ValueError, match="SEPAY_PAYMENT_CODE_PREFIX"):
        check_payment_config()


def test_prefix_too_long_raises(monkeypatch):
    monkeypatch.setattr(settings, "SEPAY_PAYMENT_CODE_PREFIX", "ORDERX")
    with pytest.raises(ValueError, match="SEPAY_PAYMENT_CODE_PREFIX"):
        check_payment_config()


def test_suffix_length_out_of_range_raises(monkeypatch):
    monkeypatch.setattr(settings, "SEPAY_PAYMENT_CODE_SUFFIX_LENGTH", 0)
    with pytest.raises(ValueError, match="SEPAY_PAYMENT_CODE_SUFFIX_LENGTH"):
        check_payment_config()


def test_code_length_exceeds_column_limit_raises(monkeypatch):
    monkeypatch.setattr(settings, "SEPAY_PAYMENT_CODE_SUFFIX_LENGTH", 30)
    with pytest.raises(ValueError, match="vuot qua"):
        check_payment_config()


def test_vietinbank_without_sevqr_raises(monkeypatch):
    """VietinBank ca nhan BAT BUOC 'SEVQR' -> thieu = mat tien."""
    monkeypatch.setattr(settings, "SEPAY_BANK_NAME", "ICB")
    monkeypatch.setattr(settings, "SEPAY_QR_CONTENT_PREFIX", "")
    with pytest.raises(ValueError, match="SEVQR"):
        check_payment_config()


def test_non_vietinbank_does_not_require_sevqr(monkeypatch):
    monkeypatch.setattr(settings, "SEPAY_BANK_NAME", "VCB")
    monkeypatch.setattr(settings, "SEPAY_QR_CONTENT_PREFIX", "")
    assert check_payment_config() == []


def test_missing_optional_settings_only_warn(monkeypatch):
    """Thieu token/secret/account -> canh bao, app van start."""
    monkeypatch.setattr(settings, "SEPAY_BANK_ACCOUNT", "")
    monkeypatch.setattr(settings, "SEPAY_WEBHOOK_SECRET", "")
    monkeypatch.setattr(settings, "SEPAY_API_TOKEN", "")
    warnings = check_payment_config()
    assert len(warnings) == 3
    assert any("SEPAY_BANK_ACCOUNT" in w for w in warnings)
    assert any("SEPAY_WEBHOOK_SECRET" in w for w in warnings)
    assert any("SEPAY_API_TOKEN" in w for w in warnings)
