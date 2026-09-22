"""Add persisted detailed key-point extraction results.

Revision ID: 20260823_002
Revises: 20260823_001_add_youtube_transcripts
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260823_002"
down_revision: Union[str, None] = "20260823_001_add_youtube_transcripts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "key_points_summaries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("key_points_text", sa.Text(), nullable=True),
        sa.Column("key_points_model", sa.String(length=50), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index("ix_key_points_summaries_job_id", "key_points_summaries", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_key_points_summaries_job_id", table_name="key_points_summaries")
    op.drop_table("key_points_summaries")
