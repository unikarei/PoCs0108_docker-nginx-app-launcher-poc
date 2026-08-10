"""Initial schema

Revision ID: 20251213_001
Revises: 
Create Date: 2025-12-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251213_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create jobs table
    op.create_table(
        'jobs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('youtube_url', sa.String(length=2048), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.Column('model', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'transcribing', 'correcting', 'completed', 'failed')",
            name='check_job_status'
        ),
        sa.CheckConstraint(
            "language IN ('ja', 'en')",
            name='check_language'
        ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_jobs_status', 'jobs', ['status'])
    op.create_index('ix_jobs_created_at', 'jobs', ['created_at'])

    # Create audio_files table
    op.create_table(
        'audio_files',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('file_path', sa.String(length=1024), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('format', sa.String(length=10), nullable=True),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audio_files_job_id', 'audio_files', ['job_id'])

    # Create transcripts table
    op.create_table(
        'transcripts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('language_detected', sa.String(length=10), nullable=True),
        sa.Column('transcription_model', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_transcripts_job_id', 'transcripts', ['job_id'])

    # Create corrected_transcripts table
    op.create_table(
        'corrected_transcripts',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('corrected_text', sa.Text(), nullable=False),
        sa.Column('original_text', sa.Text(), nullable=False),
        sa.Column('correction_model', sa.String(length=50), nullable=True),
        sa.Column('changes_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_corrected_transcripts_job_id', 'corrected_transcripts', ['job_id'])


def downgrade() -> None:
    op.drop_index('ix_corrected_transcripts_job_id', table_name='corrected_transcripts')
    op.drop_table('corrected_transcripts')
    op.drop_index('ix_transcripts_job_id', table_name='transcripts')
    op.drop_table('transcripts')
    op.drop_index('ix_audio_files_job_id', table_name='audio_files')
    op.drop_table('audio_files')
    op.drop_index('ix_jobs_created_at', table_name='jobs')
    op.drop_index('ix_jobs_status', table_name='jobs')
    op.drop_table('jobs')
