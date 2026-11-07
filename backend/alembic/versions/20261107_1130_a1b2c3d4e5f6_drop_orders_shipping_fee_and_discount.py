"""drop shipping_fee and discount from orders

Revision ID: a1b2c3d4e5f6
Revises: f4a5b6c7d8e9
Create Date: 2026-11-07 11:30:00.000000

Bo 2 cot `shipping_fee` va `discount` khoi bang `orders`:

- Chua co trien khai that cho phi ship hay discount (coupon/voucher).
  Giu cot rong co lam codebase bi hien: FE tu tinh lai cong thuc rieng,
  DB default 30.000 lech voi gia tri service ghi vao.
- `total` = `subtotal` => khong doi thay doi nghiep vu hien tai.
- Khi can tinh phi ship / discount that, them cot moi + migration Alembic
  va sua cong thuc `total` trong `app.service.order_service.create_order`.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("orders", "discount")
    op.drop_column("orders", "shipping_fee")


def downgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("shipping_fee", sa.Numeric(precision=12, scale=0), nullable=False, server_default="30000"),
    )
    op.add_column(
        "orders",
        sa.Column("discount", sa.Numeric(precision=12, scale=0), nullable=False, server_default="0"),
    )
    # Backfill total cho don da co phi ship cu (tru tien ship khi freeship).
    op.execute(
        "UPDATE orders SET total = subtotal + shipping_fee - discount WHERE total <> subtotal"
    )
