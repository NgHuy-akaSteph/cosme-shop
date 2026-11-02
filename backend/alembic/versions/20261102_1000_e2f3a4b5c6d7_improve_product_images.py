"""improve product_images schema

Revision ID: e2f3a4b5c6d7
Revises: c1d2e3f4a5b6
Create Date: 2026-11-02 10:00:00.000000

Cai thiện bang product_images cho Cloudinary:
- Drop cot `url` (http): khong dung, khong an toan, duoc suy ra tu `public_id`.
  Chi con `secure_url` lam canonical URL + fallback.
- Partial unique index (product_id) WHERE is_main: enforce "chi 1 anh main"
  ngay trong DB, chay race condition khi 2 request upload song song.
- Composite index (product_id, position): phuc vu truy van gallery ORDER BY position.
- server_default cho `position`: model co default=0 nhung DB thieu -> raw SQL
  insert se loi NOT NULL.
- Drop `ix_product_images_id`: trung voi PK `product_images_pkey`.
  Nguyen nhan: IdMixin dat `index=True` tren `primary_key` trong db/base.py.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str]] = None
depends_on: Union[str, Sequence[str]] = None


def upgrade() -> None:
    # 1. Normalize du lieu truoc khi tao partial unique index.
    #    Chi giu 1 anh main cho moi product (anh co position nho nhat).
    op.execute(
        """
        UPDATE product_images SET is_main = false
        WHERE id NOT IN (
            SELECT DISTINCT ON (product_id) id
            FROM product_images
            WHERE is_main = true
            ORDER BY product_id, position ASC, id ASC
        )
        """
    )

    # 2. Partial unique index: 1 product chi co toi da 1 anh main.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_product_images_one_main "
        "ON product_images (product_id) WHERE is_main"
    )

    # 3. Composite index cho truy van gallery theo thu tu.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_product_images_product_position "
        "ON product_images (product_id, position)"
    )

    # 4. Server default cho position (model da co default=0, DB thieu).
    op.alter_column(
        "product_images", "position", server_default=sa.text("0"), existing_type=sa.Integer()
    )

    # 5. Drop cot `url` (http) - chi giu secure_url.
    op.drop_column("product_images", "url")

    # 6. Drop index thua voi PK.
    op.execute("DROP INDEX IF EXISTS ix_product_images_id")


def downgrade() -> None:
    # Khoi phuc cot `url`: gan lai tu secure_url (doi http -> https).
    op.add_column(
        "product_images",
        sa.Column("url", sa.String(length=500), nullable=True),
    )
    op.execute(
        "UPDATE product_images SET url = secure_url WHERE url IS NULL"
    )
    op.alter_column(
        "product_images", "url", nullable=False, existing_type=sa.String(length=500)
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_product_images_id ON product_images (id)")
    op.alter_column(
        "product_images", "position", server_default=None, existing_type=sa.Integer()
    )
    op.execute("DROP INDEX IF EXISTS ix_product_images_product_position")
    op.execute("DROP INDEX IF EXISTS uq_product_images_one_main")
