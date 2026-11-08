"""Test chuan hoa gia tien: khong dung ky hieu mu (E-notation)."""

from decimal import Decimal

import pytest

from app.core.money import format_money


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("1.8E+5"), "180000"),
        (Decimal("180000"), "180000"),
        (Decimal("5.7E+5"), "570000"),
        (Decimal("180000.00"), "180000"),
        (Decimal("0"), "0"),
        (180000, "180000"),
        (None, None),
    ],
)
def test_format_money(value, expected):
    assert format_money(value) == expected


def test_format_money_no_exponent_for_large_values():
    """Gia tri >= 1e6 van phai la chuoi phang."""
    assert format_money(Decimal("1E+6")) == "1000000"
    assert format_money(Decimal("12345678.00")) == "12345678"
