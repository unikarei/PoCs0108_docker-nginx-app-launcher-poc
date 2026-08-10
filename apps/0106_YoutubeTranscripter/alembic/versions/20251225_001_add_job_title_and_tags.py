"""add job user_title and tags

Revision ID: 20251225_001
Revises: 20251218_001
Create Date: 2025-12-25
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251225_001'
down_revision = '20251218_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('user_title', sa.String(length=500), nullable=True))
    op.add_column('jobs', sa.Column('tags', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('jobs', 'tags')
    op.drop_column('jobs', 'user_title')
