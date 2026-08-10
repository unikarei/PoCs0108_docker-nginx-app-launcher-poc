"""
Export endpoints for downloading transcripts
"""
import logging
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
from services.job_manager import JobManager
from services.export_service import ExportService
from urllib.parse import quote

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{job_id}/export")
async def export_transcript(
    job_id: str,
    format: Annotated[str, Query(description="Export format: txt, srt, or vtt")] = "txt",
    db: Session = Depends(get_db)
):
    """
    Export transcript in specified format
    
    Args:
        job_id: Job ID
        format: Export format (txt, srt, vtt)
        db: Database session
        
    Returns:
        File download response
    """
    try:
        # Validate format
        format = format.lower()
        if format not in ['txt', 'srt', 'vtt']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format: {format}. Must be txt, srt, or vtt"
            )
        
        # Get job
        job_manager = JobManager(db)
        job = job_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )
        
        # Check if job is complete
        if job.status != 'completed':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job not completed. Current status: {job.status}"
            )
        
        # Determine which transcript to use
        if job.corrected_transcript:
            transcript_text = job.corrected_transcript.corrected_text
            logger.info(f"Using corrected transcript for export: {job_id}")
        elif job.transcript:
            transcript_text = job.transcript.text
            logger.info(f"Using original transcript for export: {job_id}")
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No transcript available"
            )

        # Load timestamped segments if available (from original transcript)
        segments = None
        if job.transcript and getattr(job.transcript, "segments_json", None):
            try:
                segments = json.loads(job.transcript.segments_json)
            except Exception:
                segments = None
        
        # Get audio duration
        duration_seconds = job.audio_file.duration_seconds if job.audio_file else 0
        
        # Export to requested format
        export_service = ExportService()
        
        if format == 'txt':
            content = export_service.export_to_txt(transcript_text)
            media_type = "text/plain"
            extension = "txt"
        elif format == 'srt':
            content = export_service.export_to_srt(transcript_text, duration_seconds, segments=segments)
            media_type = "application/x-subrip"
            extension = "srt"
        elif format == 'vtt':
            content = export_service.export_to_vtt(transcript_text, duration_seconds, segments=segments)
            media_type = "text/vtt"
            extension = "vtt"
        
        # Generate filename (ASCII-safe + UTF-8 variant)
        video_title = job.audio_file.title if job.audio_file and job.audio_file.title else "transcript"
        # ASCII-safe fallback (replace non-ASCII with '_')
        safe_title = "".join(
            c if c.isascii() and (c.isalnum() or c in (" ", "-", "_")) else "_"
            for c in video_title
        ).strip()
        if not safe_title:
            safe_title = "transcript"
        filename_ascii = f"{safe_title}.{extension}"
        filename_utf8 = f"{video_title}.{extension}"
        filename_utf8_quoted = quote(filename_utf8)
        
        logger.info(f"Exporting job {job_id} as {format}")
        
        return Response(
            content=content.encode('utf-8'),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename_ascii}\"; filename*=UTF-8''{filename_utf8_quoted}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export transcript: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export transcript"
        )
