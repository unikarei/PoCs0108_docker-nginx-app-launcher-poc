"""
add qa_results table

Revision ID: 20251214_001
Revises: 20251213_001
Create Date: 2025-12-14
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251214_001'
down_revision = '20251213_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'qa_results',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('answer', sa.Text(), nullable=False),
        sa.Column('qa_model', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_qa_results_job_id', 'qa_results', ['job_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_qa_results_job_id', table_name='qa_results')
    op.drop_table('qa_results')
