"""drop routine builder columns

Revision ID: b9c4d5e6f7a8
Revises: a8b3c4d5e6f7
Create Date: 2026-10-13 06:00:00.000000

Drop columns usage_time, step tu bang products (vi da loai bo module AI/Routine Builder).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9c4d5e6f7a8'
down_revision: Union[str, None] = 'a8b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('products', 'usage_time')
    op.drop_column('products', 'step')


def downgrade() -> None:
    op.add_column('products', sa.Column('usage_time', sa.String(length=20), nullable=True))
    op.add_column('products', sa.Column('step', sa.Integer(), nullable=True))
