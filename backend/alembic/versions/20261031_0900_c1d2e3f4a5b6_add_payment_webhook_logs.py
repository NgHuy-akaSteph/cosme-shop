"""add payment webhook logs

Revision ID: c1d2e3f4a5b6
Revises: b9c4d5e6f7a8
Create Date: 2026-10-31 09:00:00.000000

- Bang payment_webhook_logs luu lai webhook SePay da nhan (chong trung o muc DB)
- Unique constraint tren (provider, transaction_id) de chan giao dich trung
- Partial unique index tren orders.transaction_id de 1 giao dich chi danh 1 don
"""

from typing import Sequence, Union

import sqlalchemy.dialects.postgresql
from alembic import op
import sqlalchemy as sa

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "b9c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payment_webhook_logs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "provider", sa.String(length=20), nullable=False, server_default="sepay"
        ),
        sa.Column("transaction_id", sa.String(length=64), nullable=False),
        sa.Column("order_code", sa.String(length=32), nullable=True),
        sa.Column("amount", sa.BigInteger(), nullable=True),
        sa.Column(
            "payload", sqlalchemy.dialects.postgresql.JSONB(), nullable=True
        ),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="received"
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "provider", "transaction_id", name="uq_payment_webhook_provider_txid"
        ),
    )
    op.create_index(
        "ix_payment_webhook_logs_order_code",
        "payment_webhook_logs",
        ["order_code"],
    )
    op.create_index(
        "ix_payment_webhook_logs_status",
        "payment_webhook_logs",
        ["status"],
    )
    # 1 giao dich chi duoc gan cho 1 don -> chan cong tien / danh paid trung
    op.create_index(
        "uq_orders_transaction_id",
        "orders",
        ["transaction_id"],
        unique=True,
        postgresql_where=sa.text("transaction_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_orders_transaction_id", table_name="orders")
    op.drop_index("ix_payment_webhook_logs_status", table_name="payment_webhook_logs")
    op.drop_index("ix_payment_webhook_logs_order_code", table_name="payment_webhook_logs")
    op.drop_table("payment_webhook_logs")
