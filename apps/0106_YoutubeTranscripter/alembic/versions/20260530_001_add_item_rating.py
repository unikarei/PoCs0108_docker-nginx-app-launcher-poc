"""add item rating

Revision ID: 20260530_001_add_item_rating
Revises: 20260104_001_add_job_notes
Create Date: 2026-05-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260530_001_add_item_rating'
down_revision: Union[str, None] = '20260104_001_add_job_notes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('items', sa.Column('rating', sa.Integer(), nullable=True))
    op.create_check_constraint(
        'check_item_rating',
        'items',
        'rating IS NULL OR rating BETWEEN 1 AND 5',
    )


def downgrade() -> None:
    op.drop_constraint('check_item_rating', 'items', type_='check')
    op.drop_column('items', 'rating')