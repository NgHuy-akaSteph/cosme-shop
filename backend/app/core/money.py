"""Chuan hoa gia tri tien (Decimal) de serialize ra API.

LY DO TON TAI:
- Cot `NUMERIC(12,0)` khi doc tu Postgres (asyncpg) se decode thanh
  `Decimal('1.8E+5')` - Python luon render Decimal theo kieu "scientific
  notation" khi gia tri >= 1e6 va duoi 1e-7.
- `str(Decimal('1.8E+5'))` => `'1.8E+5'` => FE dua vao `InputNumber`
  khong parse duoc => hien thi sai (vd "1E").
- Gia tri thuc te trong DB van dung (`price::text` => `'180000'`).

GIAI PHAP: moi noi serialize tien deu dung `format_money` (format 'f' => khong
ky hieu mu) thay vi `str()`. Pydantic schema dung `MoneyDecimal` de tu
dong hoa khi response_model render JSON.
"""

from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer


def format_money(value: Decimal | int | float | None) -> str | None:
    """
    Chuyen gia tri tien thanh chuoi phang (khong ky hieu mu).

    - `Decimal('1.8E+5')` -> `'180000'`
    - `Decimal('180000.00')` -> `'180000'`
    - `None` -> `None`
    """
    if value is None:
        return None
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    # format 'f' = khong ky hieu mu (khac voi str()).
    text = format(value, "f")
    # Bo phan thap phan 0 thua: '180000.00' -> '180000'.
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


# Decimal serialize theo `format_money` khi render JSON.
MoneyDecimal = Annotated[
    Decimal,
    PlainSerializer(format_money, return_type=str, when_used="json"),
]
