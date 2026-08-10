"""
Database models for YouTube Transcription App
"""
from sqlalchemy import (
    Column, String, Integer, Text, BigInteger, Numeric,
    DateTime, ForeignKey, Index, CheckConstraint, Boolean, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from database import Base


def generate_uuid():
    """Generate UUID as string"""
    return str(uuid.uuid4())


class Job(Base):
    """
    Job model represents a transcription job
    """
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    youtube_url = Column(String(2048), nullable=False)
    # Optional title/tags provided by user (e.g., from CSV batch input)
    user_title = Column(String(500), nullable=True)
    # Semicolon-delimited tags string (e.g., "tag1;tag2")
    tags = Column(Text, nullable=True)
    language = Column(String(10), nullable=False)
    model = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    # More granular progress stage (keeps status enum/constraint unchanged for compatibility)
    stage = Column(String(30), nullable=True)
    # JSON string with stage details (e.g., chunk index/count)
    stage_detail = Column(Text, nullable=True)
    progress = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    audio_file = relationship("AudioFile", back_populates="job", uselist=False, cascade="all, delete-orphan")
    transcript = relationship("Transcript", back_populates="job", uselist=False, cascade="all, delete-orphan")
    corrected_transcript = relationship("CorrectedTranscript", back_populates="job", uselist=False, cascade="all, delete-orphan")
    qa_results = relationship("QaResult", back_populates="job", cascade="all, delete-orphan")
    note = relationship("JobNote", back_populates="job", uselist=False, cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'transcribing', 'correcting', 'completed', 'failed', 'canceled')",
            name="check_job_status"
        ),
        CheckConstraint(
            "language IN ('ja', 'en')",
            name="check_language"
        ),
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_created_at", "created_at"),
    )


class AudioFile(Base):
    """
    AudioFile model represents extracted audio from YouTube
    """
    __tablename__ = "audio_files"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(1024), nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    format = Column(String(10), nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    title = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    job = relationship("Job", back_populates="audio_file")

    # Indexes
    __table_args__ = (
        Index("ix_audio_files_job_id", "job_id"),
    )


class Transcript(Base):
    """
    Transcript model represents transcribed text from audio
    """
    __tablename__ = "transcripts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    text = Column(Text, nullable=False)
    language_detected = Column(String(10), nullable=True)
    transcription_model = Column(String(50), nullable=True)
    # JSON string for timestamped segments (for SRT/VTT). Optional for backward compatibility.
    segments_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    job = relationship("Job", back_populates="transcript")

    # Indexes
    __table_args__ = (
        Index("ix_transcripts_job_id", "job_id"),
    )


class CorrectedTranscript(Base):
    """
    CorrectedTranscript model represents LLM-corrected transcription text
    """
    __tablename__ = "corrected_transcripts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    corrected_text = Column(Text, nullable=False)
    original_text = Column(Text, nullable=False)
    correction_model = Column(String(50), nullable=True)
    changes_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    job = relationship("Job", back_populates="corrected_transcript")

    # Indexes
    __table_args__ = (
        Index("ix_corrected_transcripts_job_id", "job_id"),
    )


class QaResult(Base):
    """
    QaResult model represents Q&A entries associated with a job
    """

    __tablename__ = "qa_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    qa_model = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    job = relationship("Job", back_populates="qa_results")

    # Indexes
    __table_args__ = (
        Index("ix_qa_results_job_id", "job_id"),
    )


class JobNote(Base):
    """
    JobNote model represents a text note associated with a job
    """
    __tablename__ = "job_notes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=False)
    content = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    job = relationship("Job", back_populates="note")

    # Indexes
    __table_args__ = (
        Index("ix_job_notes_job_id", "job_id"),
    )


# ============================================================================
# Folder Tree Models (New)
# ============================================================================

class Folder(Base):
    """
    Folder model for hierarchical organization of items
    """
    __tablename__ = "folders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    parent_id = Column(String(36), ForeignKey("folders.id", ondelete="CASCADE"), nullable=True)
    path = Column(Text, nullable=False)  # Materialized path (e.g., "/Inbox/Work")
    
    # Default settings for items in this folder
    default_language = Column(String(10), nullable=True)
    default_model = Column(String(50), nullable=True)
    default_prompt = Column(Text, nullable=True)
    default_qa_enabled = Column(Boolean, default=False)
    default_output_format = Column(String(10), default='txt')
    naming_template = Column(String(500), nullable=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    color = Column(String(20), nullable=True)
    icon = Column(String(50), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    parent = relationship("Folder", remote_side=[id], back_populates="children")
    children = relationship("Folder", back_populates="parent", cascade="all, delete-orphan")
    items = relationship("Item", back_populates="folder")

    # Constraints and Indexes
    __table_args__ = (
        Index("ix_folders_parent_id", "parent_id"),
        Index("ix_folders_path", "path"),
    )


class Item(Base):
    """
    Item model represents a video/job in the folder tree
    """
    __tablename__ = "items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    folder_id = Column(String(36), ForeignKey("folders.id", ondelete="RESTRICT"), nullable=False)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=True)
    
    # Basic information
    title = Column(String(500), nullable=True)
    youtube_url = Column(Text, nullable=False)
    
    # Status (synced with jobs.status)
    status = Column(String(20), nullable=False, default='queued')
    progress = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)
    
    # Metadata
    duration_seconds = Column(Integer, nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    cost_usd = Column(Numeric(10, 4), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    folder = relationship("Folder", back_populates="items")
    job = relationship("Job", foreign_keys=[job_id])
    artifacts = relationship("Artifact", back_populates="item", cascade="all, delete-orphan")
    item_tags = relationship("ItemTag", back_populates="item", cascade="all, delete-orphan")

    # Constraints and Indexes
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed')",
            name="check_item_status"
        ),
        CheckConstraint(
            "rating IS NULL OR rating BETWEEN 1 AND 5",
            name="check_item_rating"
        ),
        Index("ix_items_folder_id", "folder_id"),
        Index("ix_items_job_id", "job_id"),
        Index("ix_items_status", "status"),
        Index("ix_items_created_at", "created_at"),
        Index("ix_items_updated_at", "updated_at"),
    )


class Artifact(Base):
    """
    Artifact model represents generated outputs (transcript, proofread, QA, etc.)
    """
    __tablename__ = "artifacts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    item_id = Column(String(36), ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    
    # Type of artifact
    artifact_type = Column(String(50), nullable=False)  # 'transcript', 'proofread', 'qa', 'export', 'summary'
    
    # References to existing tables
    transcript_id = Column(String(36), ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=True)
    corrected_transcript_id = Column(String(36), ForeignKey("corrected_transcripts.id", ondelete="CASCADE"), nullable=True)
    qa_result_id = Column(String(36), ForeignKey("qa_results.id", ondelete="CASCADE"), nullable=True)
    
    # Generic data storage
    content = Column(Text, nullable=True)
    artifact_metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    item = relationship("Item", back_populates="artifacts")
    transcript = relationship("Transcript", foreign_keys=[transcript_id])
    corrected_transcript = relationship("CorrectedTranscript", foreign_keys=[corrected_transcript_id])
    qa_result = relationship("QaResult", foreign_keys=[qa_result_id])

    # Constraints and Indexes
    __table_args__ = (
        CheckConstraint(
            "artifact_type IN ('transcript', 'proofread', 'qa', 'export', 'summary')",
            name="check_artifact_type"
        ),
        Index("ix_artifacts_item_id", "item_id"),
        Index("ix_artifacts_type", "artifact_type"),
    )


class Tag(Base):
    """
    Tag master table
    """
    __tablename__ = "tags"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, unique=True)
    color = Column(String(20), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    item_tags = relationship("ItemTag", back_populates="tag", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("ix_tags_name", "name"),
    )


class ItemTag(Base):
    """
    Many-to-many relationship between items and tags
    """
    __tablename__ = "item_tags"

    item_id = Column(String(36), ForeignKey("items.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(String(36), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    item = relationship("Item", back_populates="item_tags")
    tag = relationship("Tag", back_populates="item_tags")

    # Indexes
    __table_args__ = (
        Index("ix_item_tags_item_id", "item_id"),
        Index("ix_item_tags_tag_id", "tag_id"),
    )
