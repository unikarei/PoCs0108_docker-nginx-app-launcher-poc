"""
Job management endpoints
"""
import logging
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
import subprocess
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from kombu.exceptions import OperationalError as KombuOperationalError
from sqlalchemy.exc import OperationalError as SAOperationalError, SQLAlchemyError
from sqlalchemy import or_, func
from sqlalchemy.sql import exists
from sqlalchemy.orm import Session

from database import get_db
from models import Job, AudioFile, QaResult
from routers.schemas import (
    TranscribeJobRequest,
    TranscribeJobResponse,
    JobStatusResponse,
    JobResultResponse,
    CorrectTranscriptRequest,
    CorrectTranscriptResponse,
    ProofreadRequest,
    ProofreadResponse,
    QaRequest,
    QaResponse,
    JobListResponse,
    ExpandRequest,
    ExpandResponse,
    CancelJobResponse,
    DeleteJobResponse,
    BulkDeleteJobsRequest,
    BulkDeleteJobsResponse,
    UpdateTitleRequest,
    UpdateTitleResponse,
)
from services.job_manager import JobManager
from services.playlist_expander import (
    expand_playlist_or_channel as expand_playlist_or_channel_service,
    validate_youtube_url,
)
from worker import celery_app, transcription_task, correction_task, proofread_task, qa_task

logger = logging.getLogger(__name__)

router = APIRouter()


_DELETABLE_STATUSES = {"pending", "completed", "failed"}
_CANCELABLE_STATUSES = {"pending", "processing", "transcribing"}


def _safe_remove_path(path: Path) -> None:
    try:
        if not path.exists():
            return
        if path.is_file() or path.is_symlink():
            path.unlink(missing_ok=True)
            return
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
    except Exception as e:
        logger.warning(f"Failed to remove path {path}: {e}")


def _cleanup_job_artifacts(job: Job) -> None:
    # audio_files is bind-mounted in docker-compose; removing here clears host files too.
    audio_root = Path("audio_files").resolve()
    job_id = job.id

    # Chunk directory
    _safe_remove_path(audio_root / job_id)

    # Common single-file outputs
    for ext in ("m4a", "mp3", "webm", "wav", "aac", "opus", "m4a.part", "webm.part"):
        _safe_remove_path(audio_root / f"{job_id}.{ext}")

    # DB-stored audio file path (if present)
    try:
        file_path = getattr(getattr(job, "audio_file", None), "file_path", None)
        if isinstance(file_path, str) and file_path.strip():
            p = Path(file_path.strip())
            p = (Path.cwd() / p).resolve() if not p.is_absolute() else p.resolve()
            if audio_root in p.parents or p == audio_root:
                _safe_remove_path(p)
    except Exception:
        # best-effort cleanup only
        return


def _parse_iso_datetime(value: str) -> datetime:
    """Parse ISO datetime query param, allowing trailing 'Z'."""
    try:
        v = value.strip()
        if v.endswith("Z"):
            v = v[:-1] + "+00:00"
        return datetime.fromisoformat(v)
    except Exception as e:
        raise ValueError("Invalid datetime format. Use ISO-8601 (e.g., 2025-12-25T12:34:56Z)") from e




@router.get("/", response_model=JobListResponse)
async def list_jobs(
    db: Annotated[Session, Depends(get_db)],
    q: Optional[str] = Query(default=None, description="Keyword (title/url)"),
    tag: Optional[str] = Query(default=None, description="Single tag to match (semicolon-delimited storage)"),
    from_ts: Optional[str] = Query(default=None, alias="from", description="ISO datetime from"),
    to_ts: Optional[str] = Query(default=None, alias="to", description="ISO datetime to"),
    language: Optional[str] = Query(default=None, description="Filter by language"),
    model: Optional[str] = Query(default=None, description="Filter by model"),
    has_qa: Optional[bool] = Query(default=None, description="Filter jobs that have QA results"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """List/search jobs for Library tab."""
    try:
        has_qa_expr = exists().where(QaResult.job_id == Job.id)

        base_query = (
            db.query(
                Job,
                AudioFile.title.label("audio_title"),
                AudioFile.duration_seconds.label("duration_seconds"),
                has_qa_expr.label("has_qa"),
            )
            .outerjoin(AudioFile, AudioFile.job_id == Job.id)
        )

        if q:
            q_like = f"%{q.strip()}%"
            base_query = base_query.filter(
                or_(
                    Job.youtube_url.ilike(q_like),
                    Job.user_title.ilike(q_like),
                    AudioFile.title.ilike(q_like),
                )
            )

        if tag:
            tag_like = f"%{tag.strip()}%"
            base_query = base_query.filter(Job.tags.ilike(tag_like))

        if from_ts:
            base_query = base_query.filter(Job.created_at >= _parse_iso_datetime(from_ts))
        if to_ts:
            base_query = base_query.filter(Job.created_at <= _parse_iso_datetime(to_ts))

        if language:
            base_query = base_query.filter(Job.language == language)
        if model:
            base_query = base_query.filter(Job.model == model)

        if has_qa is True:
            base_query = base_query.filter(has_qa_expr)

        total = (
            base_query.with_entities(func.count(Job.id))
            .scalar()
        )

        rows = (
            base_query
            .order_by(Job.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        items = []
        for job, audio_title, duration_seconds, has_qa_value in rows:
            title = job.user_title or audio_title
            items.append(
                {
                    "job_id": job.id,
                    "status": job.status,
                    "youtube_url": job.youtube_url,
                    "title": title,
                    "user_title": getattr(job, "user_title", None),
                    "tags": getattr(job, "tags", None),
                    "language": job.language,
                    "model": job.model,
                    "duration_seconds": duration_seconds,
                    "has_qa": bool(has_qa_value),
                    "created_at": job.created_at,
                    "updated_at": job.updated_at,
                }
            )

        return {"items": items, "total": int(total or 0)}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list jobs",
        )


@router.post("/expand", response_model=ExpandResponse)
async def expand_url(
    request: ExpandRequest,
):
    """Expand a playlist/channel URL into individual video URLs for batch input."""
    try:
        url = validate_youtube_url(request.url)
        items = expand_playlist_or_channel_service(url)
        return {"items": items}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        message = str(e)
        if "yt-dlp is not installed" in message:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Expansion timed out")
    except Exception as e:
        logger.error(f"Failed to expand URL: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to expand URL")


@router.delete("/{job_id}", response_model=DeleteJobResponse)
async def delete_job(
    job_id: str,
    db: Annotated[Session, Depends(get_db)],
):
    """Delete a job and its related records (and best-effort remove audio artifacts)."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.status not in _DELETABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is in progress (status={job.status}). Try again after completion.",
        )

    _cleanup_job_artifacts(job)
    db.delete(job)
    db.commit()
    return {"job_id": job_id, "deleted": True}


@router.post("/bulk-delete", response_model=BulkDeleteJobsResponse)
async def bulk_delete_jobs(
    request: BulkDeleteJobsRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Bulk delete jobs. Returns per-job results; skips in-progress jobs."""
    results = []
    deleted_count = 0

    # De-duplicate while preserving order
    seen = set()
    job_ids = []
    for jid in request.job_ids:
        if jid in seen:
            continue
        seen.add(jid)
        job_ids.append(jid)

    for jid in job_ids:
        job = db.query(Job).filter(Job.id == jid).first()
        if not job:
            results.append({"job_id": jid, "deleted": False, "reason": "not_found"})
            continue

        if job.status not in _DELETABLE_STATUSES:
            results.append({"job_id": jid, "deleted": False, "reason": f"in_progress:{job.status}"})
            continue

        try:
            _cleanup_job_artifacts(job)
            db.delete(job)
            db.commit()
            deleted_count += 1
            results.append({"job_id": jid, "deleted": True, "reason": None})
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete job {jid}: {e}", exc_info=True)
            results.append({"job_id": jid, "deleted": False, "reason": "db_error"})

    return {"deleted_count": deleted_count, "results": results}


@router.post("/transcribe", response_model=TranscribeJobResponse, status_code=status.HTTP_201_CREATED)
async def create_transcription_job(
    request: TranscribeJobRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """
    Create a new transcription job
    
    Args:
        request: Job creation request
        db: Database session
        
    Returns:
        Job creation response with job ID
    """
    try:
        # Create job in database
        job_manager = JobManager(db)
        job = job_manager.create_job(
            youtube_url=request.youtube_url,
            user_title=request.user_title,
            tags=request.tags,
            language=request.language,
            model=request.model
        )

        # Submit job to task queue.
        # If queue publish fails, mark the job as failed so it does not remain
        # stuck in pending state without any worker actually processing it.
        try:
            transcription_task.apply_async(args=[job.id], task_id=job.id)
        except KombuOperationalError as e:
            msg = (
                "Task queue unavailable. Start Redis and Celery worker, then retry."
            )
            logger.error(f"Failed to enqueue job {job.id}: {e}", exc_info=True)
            job_manager.update_job_status(job.id, "failed", msg)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=msg,
            )
        except Exception as e:
            msg = (
                "Failed to enqueue transcription job. Check queue service health and retry."
            )
            logger.error(f"Unexpected enqueue failure for job {job.id}: {e}", exc_info=True)
            job_manager.update_job_status(job.id, "failed", msg)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=msg,
            )
        
        logger.info(f"Created transcription job: {job.id}")
        
        return TranscribeJobResponse(
            job_id=job.id,
            status=job.status,
            message="Transcription job created successfully"
        )
        
    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except SAOperationalError as e:
        logger.error(f"Database unavailable while creating job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable. Start PostgreSQL and retry.",
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error while creating job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while creating transcription job",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create job: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create transcription job"
        )


@router.post("/{job_id}/cancel", response_model=CancelJobResponse)
async def cancel_job(
    job_id: str,
    db: Annotated[Session, Depends(get_db)],
):
    """Cancel a queued/running transcription job from the Batch queue."""
    try:
        job_manager = JobManager(db)
        job = job_manager.get_job(job_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )

        if job.status == "canceled":
            return CancelJobResponse(
                job_id=job.id,
                status=job.status,
                message="ジョブは既に取消済みです",
            )

        if job.status not in _CANCELABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Job cannot be canceled in status={job.status}",
            )

        canceled_job = job_manager.cancel_job(job_id)
        if not canceled_job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )

        try:
            celery_app.control.revoke(job_id, terminate=True)
        except Exception as e:
            logger.warning(f"Failed to revoke celery task for job {job_id}: {e}", exc_info=True)

        return CancelJobResponse(
            job_id=canceled_job.id,
            status=canceled_job.status,
            message=canceled_job.error_message or "ジョブを取消しました",
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except SAOperationalError as e:
        logger.error(f"Database unavailable while canceling job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable. Start PostgreSQL and retry.",
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error while canceling job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while canceling job",
        )


@router.get("/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    db: Annotated[Session, Depends(get_db)]
):
    """
    Get job status
    
    Args:
        job_id: Job ID
        db: Database session
        
    Returns:
        Job status information
    """
    try:
        job_manager = JobManager(db)
        job = job_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        stage_detail = None
        if job.stage_detail:
            try:
                stage_detail = json.loads(job.stage_detail)
            except Exception:
                stage_detail = None

        return JobStatusResponse(
            job_id=job.id,
            status=job.status,
            stage=job.stage,
            stage_detail=stage_detail,
            progress=job.progress,
            youtube_url=job.youtube_url,
            user_title=getattr(job, "user_title", None),
            tags=getattr(job, "tags", None),
            language=job.language,
            model=job.model,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job status"
        )


@router.get("/{job_id}/result", response_model=JobResultResponse)
async def get_job_result(
    job_id: str,
    db: Annotated[Session, Depends(get_db)]
):
    """
    Get job result including transcription
    
    Args:
        job_id: Job ID
        db: Database session
        
    Returns:
        Complete job result with transcript
    """
    try:
        job_manager = JobManager(db)
        job = job_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        # Build response
        response = JobResultResponse(
            job_id=job.id,
            status=job.status,
            model=job.model,
            error_message=job.error_message
        )
        
        # Add audio file info if available
        if job.audio_file:
            response.audio_file = {
                "title": job.audio_file.title,
                "duration_seconds": job.audio_file.duration_seconds,
                "format": job.audio_file.format,
                "file_size_bytes": job.audio_file.file_size_bytes
            }
        
        # Add transcript if available
        if job.transcript:
            response.transcript = {
                "text": job.transcript.text,
                "language_detected": job.transcript.language_detected,
                "transcription_model": job.transcript.transcription_model,
                "created_at": job.transcript.created_at
            }
        
        # Add corrected transcript if available
        if job.corrected_transcript:
            response.corrected_transcript = {
                "corrected_text": job.corrected_transcript.corrected_text,
                "original_text": job.corrected_transcript.original_text,
                "correction_model": job.corrected_transcript.correction_model,
                "changes_summary": job.corrected_transcript.changes_summary,
                "created_at": job.corrected_transcript.created_at
            }

        if job.qa_results:
            response.qa_results = [
                {
                    "question": qa.question,
                    "answer": qa.answer,
                    "qa_model": qa.qa_model,
                    "created_at": qa.created_at,
                }
                for qa in job.qa_results
            ]
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job result: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job result"
        )


@router.patch("/{job_id}/title", response_model=UpdateTitleResponse)
async def update_job_title(
    job_id: str,
    request: UpdateTitleRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """
    Update job title
    
    Args:
        job_id: Job ID
        request: Update title request with new title
        db: Database session
        
    Returns:
        Updated title response
    """
    try:
        job_manager = JobManager(db)
        
        # Verify job exists
        job = job_manager.get_job(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        # Update the title
        success = job_manager.update_job_title(job_id, request.title)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update job title"
            )
        
        return UpdateTitleResponse(
            job_id=job_id,
            title=request.title,
            message="Title updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update job title: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update job title"
        )


@router.post("/{job_id}/correct", response_model=CorrectTranscriptResponse)
async def correct_transcript(
    job_id: str,
    request: CorrectTranscriptRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """
    Request LLM correction for transcript
    
    Args:
        job_id: Job ID
        request: Correction request
        db: Database session
        
    Returns:
        Correction request response
    """
    try:
        job_manager = JobManager(db)
        job = job_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        # Check if transcription is complete
        if job.status not in ['completed', 'correcting']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transcription not complete. Current status: {job.status}"
            )
        
        # Check if transcript exists
        if not job.transcript:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No transcript available for correction"
            )
        
        # Update job status
        job_manager.update_job_status(job_id, "correcting")
        
        # Submit correction task
        correction_task.delay(job_id, request.correction_model)
        
        logger.info(f"Started correction for job: {job_id}")
        
        return CorrectTranscriptResponse(
            job_id=job_id,
            status="correcting",
            message="Correction task started successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start correction: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start correction task"
        )


@router.post("/{job_id}/proofread", response_model=ProofreadResponse)
async def proofread_transcript(
    job_id: str,
    request: ProofreadRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """Request proofreading for transcript"""
    try:
        job_manager = JobManager(db)
        job = job_manager.get_job(job_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        if job.status not in ['completed', 'correcting']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transcription not complete. Current status: {job.status}"
            )

        if not job.transcript:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No transcript available for proofreading"
            )

        job_manager.update_job_status(job_id, "correcting", 0)
        proofread_task.delay(job_id, request.proofread_model)

        logger.info(f"Started proofread for job: {job_id} with model {request.proofread_model}")

        return ProofreadResponse(
            job_id=job_id,
            status="correcting",
            message="Proofread task started successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start proofread: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start proofread task"
        )


@router.post("/{job_id}/qa", response_model=QaResponse)
async def qa_on_transcript(
    job_id: str,
    request: QaRequest,
    db: Annotated[Session, Depends(get_db)]
):
    """Request QA generation based on transcript"""
    try:
        job_manager = JobManager(db)
        job = job_manager.get_job(job_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        if job.status not in ['completed', 'correcting']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transcription not complete. Current status: {job.status}"
            )

        if not job.transcript:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No transcript available for QA"
            )

        qa_task.delay(job_id, request.question, request.qa_model)

        logger.info(f"Started QA for job: {job_id} with model {request.qa_model}")

        return QaResponse(
            job_id=job_id,
            status="pending",
            message="QA task started successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start QA: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start QA task"
        )
