"""add job stage fields and transcript segments

Revision ID: 20251218_001
Revises: 20251214_001
Create Date: 2025-12-18
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251218_001'
down_revision = '20251214_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # jobs: stage + stage_detail
    op.add_column('jobs', sa.Column('stage', sa.String(length=30), nullable=True))
    op.add_column('jobs', sa.Column('stage_detail', sa.Text(), nullable=True))

    # transcripts: segments_json
    op.add_column('transcripts', sa.Column('segments_json', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('transcripts', 'segments_json')
    op.drop_column('jobs', 'stage_detail')
    op.drop_column('jobs', 'stage')
