"""add job_notes table

Revision ID: 20260104_001
Revises: d90cad151271
Create Date: 2026-01-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260104_001_add_job_notes'
down_revision: Union[str, None] = 'd90cad151271'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create job_notes table
    op.create_table(
        'job_notes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('job_id', sa.String(36), sa.ForeignKey('jobs.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('content', sa.Text, nullable=False, server_default=''),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create index
    op.create_index('ix_job_notes_job_id', 'job_notes', ['job_id'])


def downgrade() -> None:
    op.drop_index('ix_job_notes_job_id', table_name='job_notes')
    op.drop_table('job_notes')
