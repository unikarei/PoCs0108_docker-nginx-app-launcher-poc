"""store YouTube-provided transcript lookup results

Revision ID: 20260823_001_add_youtube_transcripts
Revises: 20260531_001_add_job_canceled_status
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260823_001_add_youtube_transcripts"
down_revision: Union[str, None] = "20260531_001_add_job_canceled_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create YouTube lookup storage and identify effective transcript source."""
    op.add_column(
        "transcripts",
        sa.Column("source", sa.String(length=20), nullable=False, server_default="audio"),
    )
    op.create_table(
        "youtube_transcripts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("job_id", sa.String(length=36), nullable=False, unique=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("video_id", sa.String(length=20), nullable=True),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("language_code", sa.String(length=20), nullable=True),
        sa.Column("language_name", sa.String(length=100), nullable=True),
        sa.Column("is_generated", sa.Boolean(), nullable=True),
        sa.Column("available_tracks_json", sa.Text(), nullable=True),
        sa.Column("segments_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_youtube_transcripts_job_id", "youtube_transcripts", ["job_id"])


def downgrade() -> None:
    """Remove YouTube lookup storage and source metadata."""
    op.drop_index("ix_youtube_transcripts_job_id", table_name="youtube_transcripts")
    op.drop_table("youtube_transcripts")
    op.drop_column("transcripts", "source")
