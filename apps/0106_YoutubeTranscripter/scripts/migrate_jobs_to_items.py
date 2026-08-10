#!/usr/bin/env python3
"""
Migrate existing Jobs to Items/Artifacts structure

This script migrates existing Job records to the new folder-based structure:
- Creates items for each job
- Creates artifacts (transcript, proofread, qa) for each job
- Places all items in the default Inbox folder
- Preserves all existing data

Usage:
    python scripts/migrate_jobs_to_items.py [--dry-run]
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
from models import (
    Job, AudioFile, Transcript, CorrectedTranscript, QaResult,
    Folder, Item, Artifact
)
import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_url():
    """Get database URL from environment or use default"""
    return os.getenv(
        'DATABASE_URL',
        'postgresql://postgres:postgres@localhost:5432/youtube_transcription'
    )


def get_or_create_inbox_folder(session):
    """Get or create the default Inbox folder"""
    inbox = session.query(Folder).filter(Folder.name == 'Inbox').first()
    
    if not inbox:
        logger.info("Creating default Inbox folder...")
        inbox = Folder(
            name='Inbox',
            parent_id=None,
            path='/Inbox',
            default_language='ja',
            default_model='gpt-4o-mini-transcribe',
            default_qa_enabled=False,
            default_output_format='txt'
        )
        session.add(inbox)
        session.flush()
        logger.info(f"Created Inbox folder with ID: {inbox.id}")
    
    return inbox


def map_job_status_to_item_status(job_status):
    """Map Job status to Item status"""
    status_map = {
        'pending': 'queued',
        'processing': 'running',
        'transcribing': 'running',
        'correcting': 'running',
        'completed': 'completed',
        'failed': 'failed'
    }
    return status_map.get(job_status, 'queued')


def migrate_job_to_item(session, job, inbox_folder, dry_run=False):
    """Migrate a single job to item/artifacts structure"""
    
    # Check if item already exists for this job
    existing_item = session.query(Item).filter(Item.job_id == job.id).first()
    if existing_item:
        logger.debug(f"Item already exists for job {job.id}, skipping")
        return existing_item, 0
    
    # Get audio file info
    audio_file = session.query(AudioFile).filter(AudioFile.job_id == job.id).first()
    
    # Create item
    item = Item(
        folder_id=inbox_folder.id,
        job_id=job.id,
        title=job.user_title or (audio_file.title if audio_file else None),
        youtube_url=job.youtube_url,
        status=map_job_status_to_item_status(job.status),
        progress=job.progress,
        error_message=job.error_message,
        duration_seconds=audio_file.duration_seconds if audio_file else None,
        file_size_bytes=audio_file.file_size_bytes if audio_file else None,
        cost_usd=None,  # Cost calculation not yet implemented
    )
    
    if not dry_run:
        session.add(item)
        session.flush()
    
    artifact_count = 0
    
    # Create transcript artifact
    transcript = session.query(Transcript).filter(Transcript.job_id == job.id).first()
    if transcript:
        artifact = Artifact(
            item_id=item.id,
            artifact_type='transcript',
            transcript_id=transcript.id,
            content=None,  # Content is in the transcript table
            artifact_metadata={
                'language_detected': transcript.language_detected,
                'transcription_model': transcript.transcription_model
            }
        )
        if not dry_run:
            session.add(artifact)
        artifact_count += 1
    
    # Create proofread artifact
    corrected = session.query(CorrectedTranscript).filter(
        CorrectedTranscript.job_id == job.id
    ).first()
    if corrected:
        artifact = Artifact(
            item_id=item.id,
            artifact_type='proofread',
            corrected_transcript_id=corrected.id,
            content=None,  # Content is in the corrected_transcripts table
            artifact_metadata={
                'correction_model': corrected.correction_model
            }
        )
        if not dry_run:
            session.add(artifact)
        artifact_count += 1
    
    # Create QA artifacts
    qa_results = session.query(QaResult).filter(QaResult.job_id == job.id).all()
    for qa_result in qa_results:
        artifact = Artifact(
            item_id=item.id,
            artifact_type='qa',
            qa_result_id=qa_result.id,
            content=None,  # Content is in the qa_results table
            artifact_metadata={
                'question': qa_result.question,
                'qa_model': qa_result.qa_model
            }
        )
        if not dry_run:
            session.add(artifact)
        artifact_count += 1
    
    return item, artifact_count


def migrate_all_jobs(dry_run=False):
    """Migrate all existing jobs to items/artifacts"""
    
    # Create database connection
    engine = create_engine(get_database_url())
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get or create Inbox folder
        inbox_folder = get_or_create_inbox_folder(session)
        
        # Get all jobs
        jobs = session.query(Job).all()
        total_jobs = len(jobs)
        
        logger.info(f"Found {total_jobs} jobs to migrate")
        
        if dry_run:
            logger.info("DRY RUN - No changes will be committed")
        
        migrated_count = 0
        artifact_count = 0
        skipped_count = 0
        
        for i, job in enumerate(jobs, 1):
            try:
                item, artifacts = migrate_job_to_item(session, job, inbox_folder, dry_run)
                
                if artifacts > 0 or item:
                    migrated_count += 1
                    artifact_count += artifacts
                    logger.info(
                        f"[{i}/{total_jobs}] Migrated job {job.id} -> item {item.id if not dry_run else 'DRY-RUN'} "
                        f"with {artifacts} artifacts"
                    )
                else:
                    skipped_count += 1
                    logger.debug(f"[{i}/{total_jobs}] Skipped job {job.id} (already migrated)")
                
            except Exception as e:
                logger.error(f"Error migrating job {job.id}: {e}")
                if not dry_run:
                    session.rollback()
                raise
        
        if not dry_run:
            session.commit()
            logger.info(f"✅ Migration completed successfully!")
        else:
            logger.info(f"✅ Dry run completed successfully!")
        
        logger.info(f"Summary:")
        logger.info(f"  Total jobs: {total_jobs}")
        logger.info(f"  Migrated: {migrated_count}")
        logger.info(f"  Skipped: {skipped_count}")
        logger.info(f"  Total artifacts created: {artifact_count}")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description='Migrate jobs to items/artifacts structure')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Perform a dry run without committing changes'
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Jobs to Items/Artifacts Migration Script")
    logger.info("=" * 60)
    
    try:
        migrate_all_jobs(dry_run=args.dry_run)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
    
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
