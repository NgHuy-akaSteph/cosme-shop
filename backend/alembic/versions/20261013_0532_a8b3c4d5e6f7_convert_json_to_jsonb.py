"""convert json to jsonb

Revision ID: a8b3c4d5e6f7
Revises: 0acfe5aae4ff
Create Date: 2026-10-13 05:32:00.000000

Chuyen cac cot JSON sang JSONB de ho tro JSONB @> (contains) operator
- products.skin_types, concerns, key_ingredients, free_from, variants
- order_items.variant_info

ALGORITHM: ALTER COLUMN ... USING ...::jsonb (in-place conversion, no rewrite needed)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8b3c4d5e6f7'
down_revision: Union[str, None] = '0acfe5aae4ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ALTER COLUMN ... TYPE jsonb USING ...::jsonb
    # Cach nay PostgreSQL thuc hien in-place conversion, khong can rewrite table.
    op.execute("ALTER TABLE products ALTER COLUMN skin_types TYPE jsonb USING skin_types::jsonb")
    op.execute("ALTER TABLE products ALTER COLUMN concerns TYPE jsonb USING concerns::jsonb")
    op.execute("ALTER TABLE products ALTER COLUMN key_ingredients TYPE jsonb USING key_ingredients::jsonb")
    op.execute("ALTER TABLE products ALTER COLUMN free_from TYPE jsonb USING free_from::jsonb")
    op.execute("ALTER TABLE products ALTER COLUMN variants TYPE jsonb USING variants::jsonb")
    op.execute("ALTER TABLE order_items ALTER COLUMN variant_info TYPE jsonb USING variant_info::jsonb")

    # Tao GIN index de query JSONB nhanh hon (contains @>)
    op.execute("CREATE INDEX IF NOT EXISTS ix_products_skin_types_gin ON products USING gin (skin_types)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_products_concerns_gin ON products USING gin (concerns)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_products_key_ingredients_gin ON products USING gin (key_ingredients)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_products_free_from_gin ON products USING gin (free_from)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_products_skin_types_gin")
    op.execute("DROP INDEX IF EXISTS ix_products_concerns_gin")
    op.execute("DROP INDEX IF EXISTS ix_products_key_ingredients_gin")
    op.execute("DROP INDEX IF EXISTS ix_products_free_from_gin")

    op.execute("ALTER TABLE products ALTER COLUMN skin_types TYPE json USING skin_types::json")
    op.execute("ALTER TABLE products ALTER COLUMN concerns TYPE json USING concerns::json")
    op.execute("ALTER TABLE products ALTER COLUMN key_ingredients TYPE json USING key_ingredients::json")
    op.execute("ALTER TABLE products ALTER COLUMN free_from TYPE json USING free_from::json")
    op.execute("ALTER TABLE products ALTER COLUMN variants TYPE json USING variants::json")
    op.execute("ALTER TABLE order_items ALTER COLUMN variant_info TYPE json USING variant_info::json")
