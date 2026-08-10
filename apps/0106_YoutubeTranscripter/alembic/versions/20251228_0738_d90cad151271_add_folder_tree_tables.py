"""add_folder_tree_tables

Revision ID: d90cad151271
Revises: 20251225_001
Create Date: 2025-12-28 07:38:38.779241

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


# revision identifiers, used by Alembic.
revision = 'd90cad151271'
down_revision = '20251225_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create folders table
    op.create_table(
        'folders',
        sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('parent_id', sa.String(36), nullable=True),
        sa.Column('path', sa.Text(), nullable=False),
        sa.Column('default_language', sa.String(10), nullable=True),
        sa.Column('default_model', sa.String(50), nullable=True),
        sa.Column('default_prompt', sa.Text(), nullable=True),
        sa.Column('default_qa_enabled', sa.Boolean(), default=False),
        sa.Column('default_output_format', sa.String(10), default='txt'),
        sa.Column('naming_template', sa.String(500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('icon', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['parent_id'], ['folders.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_folders_parent_id', 'folders', ['parent_id'])
    op.create_index('ix_folders_path', 'folders', ['path'])

    # Create items table
    op.create_table(
        'items',
        sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('folder_id', sa.String(36), nullable=False),
        sa.Column('job_id', sa.String(36), unique=True, nullable=True),
        sa.Column('title', sa.String(500), nullable=True),
        sa.Column('youtube_url', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='queued'),
        sa.Column('progress', sa.Integer(), default=0),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('cost_usd', sa.Numeric(10, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['folder_id'], ['folders.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.CheckConstraint("status IN ('queued', 'running', 'completed', 'failed')", name='check_item_status'),
    )
    op.create_index('ix_items_folder_id', 'items', ['folder_id'])
    op.create_index('ix_items_job_id', 'items', ['job_id'])
    op.create_index('ix_items_status', 'items', ['status'])
    op.create_index('ix_items_created_at', 'items', ['created_at'])
    op.create_index('ix_items_updated_at', 'items', ['updated_at'])

    # Create artifacts table
    op.create_table(
        'artifacts',
        sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('item_id', sa.String(36), nullable=False),
        sa.Column('artifact_type', sa.String(50), nullable=False),
        sa.Column('transcript_id', sa.String(36), nullable=True),
        sa.Column('corrected_transcript_id', sa.String(36), nullable=True),
        sa.Column('qa_result_id', sa.String(36), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('artifact_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['transcript_id'], ['transcripts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['corrected_transcript_id'], ['corrected_transcripts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['qa_result_id'], ['qa_results.id'], ondelete='CASCADE'),
        sa.CheckConstraint("artifact_type IN ('transcript', 'proofread', 'qa', 'export', 'summary')", name='check_artifact_type'),
    )
    op.create_index('ix_artifacts_item_id', 'artifacts', ['item_id'])
    op.create_index('ix_artifacts_type', 'artifacts', ['artifact_type'])

    # Create tags table
    op.create_table(
        'tags',
        sa.Column('id', sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('color', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_tags_name', 'tags', ['name'])

    # Create item_tags table
    op.create_table(
        'item_tags',
        sa.Column('item_id', sa.String(36), nullable=False),
        sa.Column('tag_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('item_id', 'tag_id'),
    )
    op.create_index('ix_item_tags_item_id', 'item_tags', ['item_id'])
    op.create_index('ix_item_tags_tag_id', 'item_tags', ['tag_id'])

    # Create default "Inbox" folder
    op.execute("""
        INSERT INTO folders (id, name, parent_id, path, default_language, default_model, default_qa_enabled, default_output_format)
        VALUES (
            replace(cast(gen_random_uuid() as text), '-', ''),
            'Inbox',
            NULL,
            '/Inbox',
            'ja',
            'gpt-4o-mini-transcribe',
            false,
            'txt'
        )
    """)


def downgrade() -> None:
    op.drop_table('item_tags')
    op.drop_table('tags')
    op.drop_table('artifacts')
    op.drop_table('items')
    op.drop_table('folders')
