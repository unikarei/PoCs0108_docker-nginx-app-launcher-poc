"""add job canceled status

Revision ID: 20260531_001_add_job_canceled_status
Revises: 20260530_001_add_item_rating
Create Date: 2026-05-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260531_001_add_job_canceled_status'
down_revision: Union[str, None] = '20260530_001_add_item_rating'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Alembic defaults alembic_version.version_num to VARCHAR(32), which is
    # too short for timestamp-based revision IDs used in this project.
    op.alter_column(
        'alembic_version',
        'version_num',
        existing_type=sa.String(length=32),
        type_=sa.String(length=64),
        existing_nullable=False,
    )

    op.drop_constraint('check_job_status', 'jobs', type_='check')
    op.create_check_constraint(
        'check_job_status',
        'jobs',
        "status IN ('pending', 'processing', 'transcribing', 'correcting', 'completed', 'failed', 'canceled')",
    )


def downgrade() -> None:
    op.drop_constraint('check_job_status', 'jobs', type_='check')
    op.create_check_constraint(
        'check_job_status',
        'jobs',
        "status IN ('pending', 'processing', 'transcribing', 'correcting', 'completed', 'failed')",
    )