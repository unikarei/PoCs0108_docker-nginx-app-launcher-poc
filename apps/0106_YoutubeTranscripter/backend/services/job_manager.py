"""
Job Manager Service
Handles job lifecycle, status updates, and database operations
"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import logging
from datetime import datetime
import json

from database import SessionLocal
from models import Job, AudioFile, Transcript, CorrectedTranscript, QaResult, Item, Folder

logger = logging.getLogger(__name__)

_CANCEL_MESSAGE = "ユーザーにより取消されました"
_PROTECTED_TERMINAL_STATUSES = {"canceled"}


class JobManager:
    """
    Service for managing transcription jobs
    """
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize JobManager
        
        Args:
            db: Optional database session. If not provided, creates new sessions for each operation.
        """
        self.db = db
        self._owns_session = db is None
    
    def _get_db(self) -> Session:
        """Get database session"""
        if self.db:
            return self.db
        return SessionLocal()
    
    def _close_db(self, db: Session):
        """Close database session if we own it"""
        if self._owns_session and db:
            db.close()
    
    def create_job(
        self,
        youtube_url: str,
        language: str,
        model: str,
        user_title: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> Job:
        """
        Create a new transcription job and corresponding Item in Inbox folder
        
        Args:
            youtube_url: YouTube video URL
            language: Target language (ja or en)
            model: Whisper model to use
            user_title: Optional user-provided title
            tags: Optional semicolon-delimited tags
            
        Returns:
            Job: Created job object
        """
        db = self._get_db()
        try:
            # Create Job
            job = Job(
                youtube_url=youtube_url,
                user_title=user_title,
                tags=tags,
                language=language,
                model=model,
                status="pending",
                progress=0,
            )
            db.add(job)
            db.flush()  # Get job.id without committing
            
            # Get or create Inbox folder
            inbox_folder = db.query(Folder).filter(Folder.name == 'Inbox').first()
            if not inbox_folder:
                inbox_folder = Folder(
                    name='Inbox',
                    path='/Inbox',
                    icon='📥',
                    description='Default folder for new items'
                )
                db.add(inbox_folder)
                db.flush()
            
            # Create Item in Inbox folder
            item = Item(
                folder_id=inbox_folder.id,
                job_id=job.id,
                title=user_title,
                youtube_url=youtube_url,
                status='queued',
                progress=0,
            )
            db.add(item)
            
            db.commit()
            db.refresh(job)
            
            logger.info(f"Created job {job.id} and item in Inbox for {youtube_url}")
            return job
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create job and item: {e}", exc_info=True)
            raise
        finally:
            self._close_db(db)
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get job by ID
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job object or None
        """
        db = self._get_db()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            return job
        finally:
            self._close_db(db)

    def is_job_canceled(self, job_id: str) -> bool:
        """Return True when the job has already been canceled."""
        db = self._get_db()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            return bool(job and job.status == "canceled")
        finally:
            self._close_db(db)

    def cancel_job(self, job_id: str, reason: Optional[str] = None) -> Optional[Job]:
        """Cancel a queued/running job and sync the linked Item state."""
        db = self._get_db()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return None

            if job.status == "canceled":
                return job

            if job.status in {"completed", "failed"}:
                raise ValueError(f"Job is already finished (status={job.status})")

            message = reason or _CANCEL_MESSAGE
            job.status = "canceled"
            job.error_message = message
            job.stage = None
            job.stage_detail = None
            job.updated_at = datetime.utcnow()

            item = db.query(Item).filter(Item.job_id == job_id).first()
            if item:
                # Keep the existing Item status enum unchanged and surface cancellations as a stopped/failed item.
                item.status = "failed"
                item.error_message = message
                item.updated_at = datetime.utcnow()

            db.commit()
            db.refresh(job)
            logger.info(f"Canceled job {job_id}")
            return job
        except Exception:
            db.rollback()
            raise
        finally:
            self._close_db(db)
    
    def update_job_status(
        self,
        job_id: str,
        status: str,
        error_message: Optional[str] = None,
        stage: Optional[str] = None,
        stage_detail: Optional[Dict[str, Any]] = None,
    ):
        """
        Update job status and sync with corresponding Item
        
        Args:
            job_id: Job identifier
            status: New status
            error_message: Error message if status is failed
            stage: Optional granular stage (download_extract|preprocess|transcribe|merge|export)
            stage_detail: Optional structured detail (e.g., chunk index/count)
        """
        db = self._get_db()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                if job.status in _PROTECTED_TERMINAL_STATUSES and status != job.status:
                    logger.info(f"Skip status update for canceled job {job_id}: {status}")
                    return

                job.status = status
                if error_message is not None:
                    job.error_message = error_message

                if stage is not None:
                    job.stage = stage

                if stage_detail is not None:
                    job.stage_detail = json.dumps(stage_detail, ensure_ascii=False)

                job.updated_at = datetime.utcnow()
                
                # Sync Item status
                item = db.query(Item).filter(Item.job_id == job_id).first()
                if item:
                    # Map job status to item status
                    status_map = {
                        'pending': 'queued',
                        'processing': 'running',
                        'transcribing': 'running',
                        'completed': 'completed',
                        'failed': 'failed',
                        'canceled': 'failed',
                    }
                    item.status = status_map.get(status, 'running')
                    if error_message is not None:
                        item.error_message = error_message
                    item.updated_at = datetime.utcnow()
                
                db.commit()
                
                logger.info(f"Updated job {job_id} status to {status}")
            else:
                logger.warning(f"Job {job_id} not found")
                
        finally:
            self._close_db(db)
    
    def update_job_progress(self, job_id: str, progress: int, message: Optional[str] = None):
        """
        Update job progress and sync with Item
        
        Args:
            job_id: Job identifier
            progress: Progress percentage (0-100)
            message: Optional progress message
        """
        db = self._get_db()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                if job.status in _PROTECTED_TERMINAL_STATUSES:
                    logger.info(f"Skip progress update for canceled job {job_id}: {progress}%")
                    return

                job.progress = progress
                job.updated_at = datetime.utcnow()
                
                # Sync Item progress
                item = db.query(Item).filter(Item.job_id == job_id).first()
                if item:
                    item.progress = progress
                    item.updated_at = datetime.utcnow()
                
                db.commit()
                
                logger.debug(f"Updated job {job_id} progress to {progress}%")
            else:
                logger.warning(f"Job {job_id} not found")
                
        finally:
            self._close_db(db)

    def update_job_title(self, job_id: str, title: str) -> bool:
        """
        Update job title (user_title) and sync with Item
        
        Args:
            job_id: Job identifier
            title: New title
            
        Returns:
            True if successful, False if job not found
        """
        db = self._get_db()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                logger.warning(f"Job {job_id} not found for title update")
                return False
            
            job.user_title = title
            job.updated_at = datetime.utcnow()
            
            # Sync Item title
            item = db.query(Item).filter(Item.job_id == job_id).first()
            if item:
                item.title = title
                item.updated_at = datetime.utcnow()
            
            db.commit()
            
            logger.info(f"Updated job {job_id} title to: {title[:50]}...")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update job title: {e}", exc_info=True)
            return False
        finally:
            self._close_db(db)
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status information
        
        Args:
            job_id: Job identifier
            
        Returns:
            Dict with job status info or None
        """
        db = self._get_db()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return None
            
            return {
                "job_id": job.id,
                "status": job.status,
                "stage": job.stage,
                "stage_detail": job.stage_detail,
                "progress": job.progress,
                "error_message": job.error_message,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
            }
            
        finally:
            self._close_db(db)
    
    def create_audio_file(
        self,
        job_id: str,
        file_path: str,
        duration_seconds: int,
        title: str,
        file_format: str,
        file_size_bytes: Optional[int] = None
    ) -> str:
        """
        Create audio file record and update corresponding Item with title and duration
        
        Args:
            job_id: Job identifier
            file_path: Path to audio file
            duration_seconds: Audio duration
            title: Video title
            file_format: Audio format (m4a, mp3, etc)
            file_size_bytes: File size in bytes
            
        Returns:
            str: Audio file ID
        """
        db = self._get_db()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job and job.status == "canceled":
                logger.info(f"Skip audio file creation for canceled job {job_id}")
                return ""

            audio_file = AudioFile(
                job_id=job_id,
                file_path=file_path,
                duration_seconds=duration_seconds,
                title=title,
                format=file_format,
                file_size_bytes=file_size_bytes
            )
            db.add(audio_file)
            
            # Update corresponding Item with title and duration
            item = db.query(Item).filter(Item.job_id == job_id).first()
            if item:
                if not item.title or item.title == '':
                    item.title = title
                item.duration_seconds = duration_seconds
                if file_size_bytes:
                    item.file_size_bytes = file_size_bytes
                item.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(audio_file)
            
            logger.info(f"Created audio file record {audio_file.id} for job {job_id}, updated Item title")
            return audio_file.id
            
        finally:
            self._close_db(db)
    
    def save_job_result(self, job_id: str, transcript: str, metadata: Dict[str, Any]):
        """
        Save transcription result
        
        Args:
            job_id: Job identifier
            transcript: Transcribed text
            metadata: Additional metadata
        """
        db = self._get_db()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job and job.status == "canceled":
                logger.info(f"Skip transcript save for canceled job {job_id}")
                return

            segments = metadata.get("segments")
            segments_json = None
            # Only persist segments when we actually have timestamped data.
            # Treat empty list as "no timestamps".
            if segments:
                try:
                    segments_json = json.dumps(segments, ensure_ascii=False)
                except TypeError:
                    # Best-effort fallback
                    segments_json = json.dumps(list(segments), ensure_ascii=False)

            transcript_record = Transcript(
                job_id=job_id,
                text=transcript,
                language_detected=metadata.get('language_detected'),
                transcription_model=metadata.get('model'),
                segments_json=segments_json,
            )
            db.add(transcript_record)
            db.commit()
            
            logger.info(f"Saved transcript for job {job_id}")
            
        finally:
            self._close_db(db)

    def upsert_corrected_transcript(
        self,
        job_id: str,
        corrected_text: str,
        original_text: str,
        correction_model: str,
        changes_summary: str,
    ) -> None:
        """Save or replace corrected transcript"""
        db = self._get_db()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job and job.status == "canceled":
                logger.info(f"Skip corrected transcript upsert for canceled job {job_id}")
                return

            existing = db.query(CorrectedTranscript).filter(CorrectedTranscript.job_id == job_id).first()
            if existing:
                db.delete(existing)
                db.commit()

            corrected = CorrectedTranscript(
                job_id=job_id,
                corrected_text=corrected_text,
                original_text=original_text,
                correction_model=correction_model,
                changes_summary=changes_summary,
            )
            db.add(corrected)
            db.commit()
            logger.info(f"Upserted corrected transcript for job {job_id}")
        finally:
            self._close_db(db)

    def create_qa_result(self, job_id: str, question: str, answer: str, qa_model: str) -> str:
        """Persist QA result"""
        db = self._get_db()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job and job.status == "canceled":
                logger.info(f"Skip QA result save for canceled job {job_id}")
                return ""

            qa = QaResult(
                job_id=job_id,
                question=question,
                answer=answer,
                qa_model=qa_model,
            )
            db.add(qa)
            db.commit()
            db.refresh(qa)
            logger.info(f"Saved QA result for job {job_id}")
            return qa.id
        finally:
            self._close_db(db)
