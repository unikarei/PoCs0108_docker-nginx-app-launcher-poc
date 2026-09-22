"""
Celery worker for YouTube Transcription App
Defines background tasks for audio extraction, transcription, and correction
"""
from celery import Celery
from celery.utils.log import get_task_logger
import os
from dotenv import load_dotenv

from database import SessionLocal
from models import Job
from services.audio_extractor import AudioExtractor
from services.audio_preprocessor import AudioPreprocessor
from services.transcription_service import TranscriptionService
from services.correction_service import CorrectionService
from services.qa_service import QaService
from services.key_points_service import KeyPointsService
from services.job_manager import JobManager
from services.transcript_merger import merge_transcripts
from services.youtube_transcript_service import YouTubeTranscriptResult, retrieve_youtube_transcript
from services.rich_text import to_plain_text
from services.job_title import build_default_job_title

load_dotenv()

# Initialize Celery app
celery_app = Celery(
    "youtube_transcription",
    broker=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://redis:6379/0"),
)

# Load configuration from celery_config
celery_app.config_from_object("celery_config")

# Setup logger
logger = get_task_logger(__name__)


def _should_stop_for_cancellation(job_manager: JobManager, job_id: str) -> bool:
    """Check whether the job was canceled and should stop early."""
    if not job_manager.is_job_canceled(job_id):
        return False

    logger.info(f"Stopping canceled transcription task for job {job_id}")
    return True


def _complete_transcription_failure(youtube_result: YouTubeTranscriptResult, audio_error: str) -> str:
    """Combine a YouTube lookup outcome with the final audio fallback error."""
    if youtube_result.status == "error":
        return f"YouTube transcript retrieval failed and audio transcription also failed: {audio_error}"
    return f"No usable YouTube-provided transcript was available; audio transcription also failed: {audio_error}"


def _queue_automatic_proofread(job_id: str, proofread_model: str) -> None:
    """Queue proofreading after Transcript has produced its effective text."""
    job_manager = JobManager()
    job_manager.update_job_progress(job_id, 100)
    job_manager.update_job_status(
        job_id,
        "correcting",
        stage="proofread",
        stage_detail={"status": "queued", "model": proofread_model},
    )
    proofread_task.delay(job_id, proofread_model)


def _set_default_title_if_needed(
    job_manager: JobManager,
    job_id: str,
    metadata: dict,
    created_at,
) -> None:
    """Persist the generated title without replacing a user title."""
    current_job = job_manager.get_job(job_id)
    if current_job and not current_job.user_title:
        job_manager.update_job_title(
            job_id,
            build_default_job_title(metadata, created_at),
        )


@celery_app.task(
    bind=True,
    name="worker.transcription_task",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def transcription_task(self, job_id: str, proofread_model: str = "gpt-4o-mini"):
    """
    Background task for transcribing YouTube audio
    
    Args:
        job_id: Unique job identifier
        proofread_model: LLM model for the automatic proofreading step
    
    Returns:
        dict: Result containing job_id and status
    """
    logger.info(f"Starting transcription task for job {job_id}")
    
    db = SessionLocal()
    job_manager = JobManager()
    
    try:
        # Get job from database
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return {"job_id": job_id, "status": "failed", "error": "Job not found"}

        # Fetch metadata once so subtitle-only jobs can also receive a useful
        # Library title without downloading audio.
        video_metadata = AudioExtractor().get_video_info(job.youtube_url) or {}

        if _should_stop_for_cancellation(job_manager, job_id):
            return {"job_id": job_id, "status": "canceled"}
        
        # Check YouTube-provided subtitles before downloading any audio.
        job_manager.update_job_status(
            job_id,
            "processing",
            stage="youtube_transcript",
            stage_detail={"status": "checking"},
        )
        job_manager.update_job_progress(job_id, 5)

        youtube_result = retrieve_youtube_transcript(job.youtube_url, job.language)
        job_manager.save_youtube_transcript_result(job_id, youtube_result)

        if youtube_result.usable:
            logger.info("Using YouTube transcript for job %s; skipping audio/STT", job_id)
            job_manager.update_job_progress(job_id, 92)
            job_manager.update_job_status(
                job_id,
                "processing",
                stage="export",
                stage_detail={"source": "youtube", "language_code": youtube_result.language_code},
            )
            job_manager.save_job_result(
                job_id=job_id,
                transcript=youtube_result.text or "",
                metadata={
                    "language_detected": youtube_result.language_code,
                    "model": "youtube-transcript",
                    "source": "youtube",
                    "segments": youtube_result.segments,
                },
            )
            _set_default_title_if_needed(job_manager, job_id, video_metadata, job.created_at)
            job_manager.update_job_progress(job_id, 100)
            job_manager.update_job_status(
                job_id,
                "correcting",
                stage="export",
                stage_detail={"source": "youtube", "segment_count": len(youtube_result.segments)},
            )
            _queue_automatic_proofread(job_id, proofread_model)
            return {"job_id": job_id, "status": "correcting", "transcript_source": "youtube"}

        logger.info(
            "No usable YouTube transcript for job %s (%s); continuing with audio fallback",
            job_id,
            youtube_result.status,
        )

        # Existing audio path remains the fallback when YouTube subtitles are unavailable.
        job_manager.update_job_status(job_id, "processing", stage="download_extract")
        
        # Step 1: Extract audio from YouTube
        logger.info(f"Extracting audio for job {job_id}")
        audio_extractor = AudioExtractor()
        
        extraction_result = audio_extractor.extract_audio(
            job_id=job_id,
            youtube_url=job.youtube_url
        )

        if _should_stop_for_cancellation(job_manager, job_id):
            return {"job_id": job_id, "status": "canceled"}
        
        if not extraction_result.success:
            logger.error(f"Audio extraction failed for job {job_id}: {extraction_result.error}")
            error = _complete_transcription_failure(youtube_result, extraction_result.error or "Audio extraction failed")
            job_manager.update_job_status(job_id, "failed", error)
            return {"job_id": job_id, "status": "failed", "error": error}
        
        # Save audio file info
        if _should_stop_for_cancellation(job_manager, job_id):
            return {"job_id": job_id, "status": "canceled"}

        job_manager.create_audio_file(
            job_id=job_id,
            file_path=extraction_result.audio_path,
            duration_seconds=extraction_result.duration_seconds,
            title=extraction_result.title,
            file_format=extraction_result.format or "m4a",
            file_size_bytes=extraction_result.file_size_bytes
        )
        
        job_manager.update_job_progress(job_id, 35)

        # Step 2: Preprocess audio if needed (compress/split)
        logger.info(f"Preprocessing audio for job {job_id}")
        job_manager.update_job_status(job_id, "processing", stage="preprocess")

        preprocessor = AudioPreprocessor(work_root="audio_files")
        preprocess_result = preprocessor.prepare_for_upload(
            audio_file_path=extraction_result.audio_path,
            job_id=job_id,
            model=job.model,
            duration_seconds=extraction_result.duration_seconds,
        )

        if _should_stop_for_cancellation(job_manager, job_id):
            return {"job_id": job_id, "status": "canceled"}

        if not preprocess_result.success or not preprocess_result.plan:
            err = preprocess_result.error or "Audio preprocess failed"
            logger.error(f"Audio preprocess failed for job {job_id}: {err}")
            error = _complete_transcription_failure(youtube_result, err)
            job_manager.update_job_status(job_id, "failed", error, stage="preprocess")
            return {"job_id": job_id, "status": "failed", "error": error}

        chunks = preprocess_result.plan.chunks
        job_manager.update_job_progress(job_id, 45)
        
        # Step 3: Transcribe per chunk
        logger.info(f"Transcribing audio for job {job_id} (chunks={len(chunks)})")
        job_manager.update_job_status(
            job_id,
            "transcribing",
            stage="transcribe",
            stage_detail={"chunk_index": 0, "chunk_count": len(chunks)},
        )

        transcription_service = TranscriptionService()
        chunk_results = []
        detected_language = None

        for i, chunk in enumerate(chunks):
            if _should_stop_for_cancellation(job_manager, job_id):
                return {"job_id": job_id, "status": "canceled"}

            job_manager.update_job_status(
                job_id,
                "transcribing",
                stage="transcribe",
                stage_detail={
                    "chunk_index": i + 1,
                    "chunk_count": len(chunks),
                    "chunk_size_bytes": chunk.size_bytes,
                },
            )

            # Progress: allocate 45-90 to transcription
            if len(chunks) > 0:
                progress = 45 + int(((i + 1) / len(chunks)) * 45)
                job_manager.update_job_progress(job_id, progress)

            transcription_result = transcription_service.transcribe_audio(
                audio_path=chunk.path,
                language=job.language,
                model=job.model,
            )

            if _should_stop_for_cancellation(job_manager, job_id):
                return {"job_id": job_id, "status": "canceled"}

            if not transcription_result.success:
                err = transcription_result.error or "Transcription failed"
                detailed = f"Chunk {i + 1}/{len(chunks)} failed: {err}"
                logger.error(f"Transcription failed for job {job_id}: {detailed}")
                error = _complete_transcription_failure(youtube_result, detailed)
                job_manager.update_job_status(job_id, "failed", error, stage="transcribe")
                return {"job_id": job_id, "status": "failed", "error": error}

            if detected_language is None and transcription_result.language_detected:
                detected_language = transcription_result.language_detected

            chunk_results.append((transcription_result.text or "", transcription_result.segments, float(chunk.start_offset_sec)))

        # Step 4: Merge
        if _should_stop_for_cancellation(job_manager, job_id):
            return {"job_id": job_id, "status": "canceled"}

        job_manager.update_job_status(job_id, "processing", stage="merge")
        job_manager.update_job_progress(job_id, 92)

        merged = merge_transcripts(chunk_results, overlap_sec=float(preprocess_result.plan.chunk_overlap_sec))

        # Step 5: Export preparation (timestamps are already continuous in merged.segments)
        if _should_stop_for_cancellation(job_manager, job_id):
            return {"job_id": job_id, "status": "canceled"}

        job_manager.update_job_status(job_id, "processing", stage="export")
        job_manager.update_job_progress(job_id, 96)

        # Save transcript (+ segments)
        if _should_stop_for_cancellation(job_manager, job_id):
            return {"job_id": job_id, "status": "canceled"}

        job_manager.save_job_result(
            job_id=job_id,
            transcript=merged.text,
            metadata={
                "language_detected": detected_language,
                "model": job.model,
                "source": "audio",
                "segments": merged.segments,
            },
        )

        _set_default_title_if_needed(job_manager, job_id, video_metadata, job.created_at)

        if _should_stop_for_cancellation(job_manager, job_id):
            return {"job_id": job_id, "status": "canceled"}

        job_manager.update_job_progress(job_id, 100)
        _queue_automatic_proofread(job_id, proofread_model)

        logger.info(f"Transcription task completed for job {job_id}")
        return {"job_id": job_id, "status": "correcting", "transcript_length": len(merged.text)}
        
    except Exception as exc:
        if job_manager.is_job_canceled(job_id):
            logger.info(f"Ignore exception after cancellation for job {job_id}: {exc}")
            return {"job_id": job_id, "status": "canceled"}

        logger.error(f"Transcription task failed for job {job_id}: {exc}", exc_info=True)
        job_manager.update_job_status(job_id, "failed", str(exc))
        # Retry the task with exponential backoff
        raise self.retry(exc=exc)
    
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="worker.correction_task",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def correction_task(self, job_id: str, correction_model: str = "gpt-4o-mini"):
    """
    Background task for correcting transcription with LLM
    
    Args:
        job_id: Unique job identifier
        correction_model: LLM model to use for correction
    
    Returns:
        dict: Result containing job_id and corrected text
    """
    logger.info(f"Starting correction task for job {job_id}")
    
    db = SessionLocal()
    job_manager = JobManager()
    
    try:
        # Get job from database
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return {"job_id": job_id, "status": "failed", "error": "Job not found"}
        
        # Check if transcript exists
        if not job.transcript:
            logger.error(f"No transcript found for job {job_id}")
            job_manager.update_job_status(job_id, "failed", "No transcript available")
            return {"job_id": job_id, "status": "failed", "error": "No transcript available"}
        
        # Update status to correcting
        job_manager.update_job_status(job_id, "correcting")
        job_manager.update_job_progress(job_id, 10)
        
        # Perform LLM correction
        logger.info(f"Correcting transcript for job {job_id}")
        correction_service = CorrectionService()
        
        correction_result = correction_service.correct_transcript(
            transcript=to_plain_text(job.transcript.text),
            language=job.language,
            model=correction_model
        )
        
        if not correction_result.success:
            logger.error(f"Correction failed for job {job_id}: {correction_result.error}")
            job_manager.update_job_status(job_id, "failed", correction_result.error)
            return {"job_id": job_id, "status": "failed", "error": correction_result.error}
        
        # Save corrected transcript
        job_manager.upsert_corrected_transcript(
            job_id=job_id,
            corrected_text=correction_result.corrected_text,
            original_text=to_plain_text(job.transcript.text),
            correction_model=correction_model,
            changes_summary=correction_result.changes_summary,
        )
        
        job_manager.update_job_progress(job_id, 100)
        job_manager.update_job_status(job_id, "completed")
        
        logger.info(f"Correction task completed for job {job_id}")
        return {
            "job_id": job_id,
            "status": "completed",
            "corrected_length": len(correction_result.corrected_text)
        }
        
    except Exception as exc:
        logger.error(f"Correction task failed for job {job_id}: {exc}", exc_info=True)
        job_manager.update_job_status(job_id, "failed", str(exc))
        # Retry the task with exponential backoff
        raise self.retry(exc=exc)
    
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="worker.proofread_task",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def proofread_task(self, job_id: str, model: str = "gpt-4o-mini"):
    """Proofread transcript with selectable LLM"""
    logger.info(f"Starting proofread task for job {job_id}")

    db = SessionLocal()
    job_manager = JobManager()

    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return {"job_id": job_id, "status": "failed", "error": "Job not found"}

        if not job.transcript:
            logger.error(f"No transcript found for job {job_id}")
            job_manager.update_job_status(job_id, "failed", "No transcript available")
            return {"job_id": job_id, "status": "failed", "error": "No transcript available"}

        job_manager.update_job_status(job_id, "correcting")
        job_manager.update_job_progress(job_id, 10)

        correction_service = CorrectionService()
        correction_result = correction_service.correct_transcript(
            transcript=to_plain_text(job.transcript.text),
            language=job.language,
            model=model,
        )

        if not correction_result.success:
            logger.error(f"Proofread failed for job {job_id}: {correction_result.error}")
            job_manager.update_job_status(job_id, "failed", correction_result.error)
            return {"job_id": job_id, "status": "failed", "error": correction_result.error}

        job_manager.upsert_corrected_transcript(
            job_id=job_id,
            corrected_text=correction_result.corrected_text,
            original_text=to_plain_text(job.transcript.text),
            correction_model=model,
            changes_summary=correction_result.changes_summary,
        )

        job_manager.update_job_progress(job_id, 100)
        job_manager.update_job_status(job_id, "completed")

        logger.info(f"Proofread task completed for job {job_id}")
        return {"job_id": job_id, "status": "completed"}

    except Exception as exc:
        logger.error(f"Proofread task failed for job {job_id}: {exc}", exc_info=True)
        job_manager.update_job_status(job_id, "failed", str(exc))
        raise self.retry(exc=exc)

    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="worker.key_points_task",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def key_points_task(self, job_id: str, model: str = "gpt-4o-mini", prompt: str = ""):
    """Generate and persist detailed key points without changing the transcript."""
    logger.info("Starting key-point extraction for job %s", job_id)

    db = SessionLocal()
    job_manager = JobManager()

    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return {"job_id": job_id, "status": "failed", "error": "Job not found"}
        if not job.transcript:
            error_message = "No transcript available for key-point extraction"
            job_manager.upsert_key_points_summary(job_id, prompt, model, "error", error_message=error_message)
            return {"job_id": job_id, "status": "failed", "error": error_message}

        job_manager.update_job_status(job_id, "correcting")
        service = KeyPointsService()
        result = service.extract(to_plain_text(job.transcript.text), prompt, model)
        if not result.success:
            error_message = result.error or "Key-point extraction failed"
            job_manager.upsert_key_points_summary(job_id, prompt, model, "error", error_message=error_message)
            job_manager.update_job_status(job_id, "completed")
            return {"job_id": job_id, "status": "failed", "error": error_message}

        job_manager.upsert_key_points_summary(
            job_id=job_id,
            prompt=prompt,
            model=model,
            status="completed",
            key_points_text=result.text,
        )
        job_manager.update_job_progress(job_id, 100)
        job_manager.update_job_status(job_id, "completed")
        logger.info("Key-point extraction completed for job %s", job_id)
        return {"job_id": job_id, "status": "completed"}
    except Exception as exc:
        logger.error("Key-point extraction task failed for %s: %s", job_id, exc, exc_info=True)
        job_manager.upsert_key_points_summary(job_id, prompt, model, "error", error_message=str(exc))
        job_manager.update_job_status(job_id, "completed")
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="worker.qa_task",
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def qa_task(self, job_id: str, question: str, model: str = "gpt-4o-mini"):
    """Answer user question based on transcript/proofread text"""
    logger.info(f"Starting QA task for job {job_id}")

    db = SessionLocal()
    job_manager = JobManager()

    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return {"job_id": job_id, "status": "failed", "error": "Job not found"}

        if not job.transcript:
            logger.error(f"No transcript found for job {job_id}")
            return {"job_id": job_id, "status": "failed", "error": "No transcript available"}

        base_text = (
            to_plain_text(job.corrected_transcript.corrected_text)
            if job.corrected_transcript
            else to_plain_text(job.transcript.text)
        )

        qa_service = QaService()
        qa_result = qa_service.answer_question(transcript_text=base_text, question=question, model=model)

        if not qa_result.success:
            logger.error(f"QA failed for job {job_id}: {qa_result.error}")
            return {"job_id": job_id, "status": "failed", "error": qa_result.error}

        job_manager.create_qa_result(job_id=job_id, question=question, answer=qa_result.answer or "", qa_model=model)

        logger.info(f"QA task completed for job {job_id}")
        return {"job_id": job_id, "status": "completed"}

    except Exception as exc:
        logger.error(f"QA task failed for job {job_id}: {exc}", exc_info=True)
        raise self.retry(exc=exc)

    finally:
        db.close()


if __name__ == "__main__":
    # Start worker when run directly
    celery_app.worker_main(["worker", "--loglevel=info"])
