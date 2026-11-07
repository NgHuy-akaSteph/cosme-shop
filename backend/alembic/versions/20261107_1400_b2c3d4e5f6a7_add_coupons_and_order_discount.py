"""add coupons table and order discount columns

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-11-07 14:00:00.000000

Trien khai ma giam gia (coupon) muc do don gian:

- Bang `coupons`: ma giam gia percent/fixed, han muc, so lan dung, thoi han.
- `orders.discount_code` + `orders.discount_amount`: SNAPSHOT so tien giam
  tai thoi diem dat hang => admin sua/xoa coupon sau do khong lam thay doi
  lich su don cu.
- `total` = `subtotal` - `discount_amount`.

Khong tao bang `coupon_usages`: dem luot dung bang atomic UPDATE tren
`coupons.used_count` (xem `app.service.discount_service.consume_coupon`).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "coupons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("discount_type", sa.String(length=10), server_default="percent", nullable=False),
        sa.Column("discount_value", sa.Integer(), nullable=False),
        sa.Column("min_order_amount", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_discount", sa.Integer(), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_coupons_id", "coupons", ["id"], unique=False)
    op.create_index("ix_coupons_code", "coupons", ["code"], unique=False)

    op.add_column("orders", sa.Column("discount_code", sa.String(length=32), nullable=True))
    op.add_column(
        "orders",
        sa.Column(
            "discount_amount",
            sa.Numeric(precision=12, scale=0),
            server_default="0",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("orders", "discount_amount")
    op.drop_column("orders", "discount_code")
    op.drop_index("ix_coupons_code", table_name="coupons")
    op.drop_index("ix_coupons_id", table_name="coupons")
    op.drop_table("coupons")
