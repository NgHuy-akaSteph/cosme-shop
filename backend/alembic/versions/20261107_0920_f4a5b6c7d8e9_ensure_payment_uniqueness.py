"""ensure payment uniqueness constraints

Revision ID: f4a5b6c7d8e9
Revises: e2f3a4b5c6d7
Create Date: 2026-11-07 09:20:00.000000

Constraint chong trung bi BO SOT khi DB duoc tao boi `create_all` thay vi alembic:

- `uq_orders_transaction_id` (partial unique): 1 giao dich ngan hang chi gan cho
  1 don. CHECK o tang application (`update_payment_status`) co race condition:
  2 request dong thoi (webhook + reconcile) deu doc "khong thay duplicate" truoc
  khi ghi => ca 2 don cung `paid`. Unique index o DB la chot chong cuoi cung.
- `uq_payment_webhook_provider_txid`: 1 giao dich chi tao 1 dong log webhook.

`CREATE UNIQUE INDEX IF NOT EXISTS` => idempotent, chay lai khong loi.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1 giao dich chi gan cho 1 don -> chan cong tien / danh paid trung
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_orders_transaction_id "
        "ON public.orders (transaction_id) WHERE transaction_id IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_payment_webhook_provider_txid "
        "ON public.payment_webhook_logs (provider, transaction_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS public.uq_payment_webhook_provider_txid")
    op.execute("DROP INDEX IF EXISTS public.uq_orders_transaction_id")
