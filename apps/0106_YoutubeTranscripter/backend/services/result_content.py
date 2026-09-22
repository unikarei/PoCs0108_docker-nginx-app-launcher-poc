"""Validated updates for editable result content."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import Job, QaResult


SUPPORTED_CONTENT_TYPES = {
    "youtube_transcript",
    "transcript",
    "proofread",
    "key_points",
    "qa_question",
    "qa_answer",
    "note",
}


class ResultContentNotFound(ValueError):
    """Raised when the requested editable result record does not exist."""


def update_result_content(
    db: Session,
    job: Job,
    content_type: str,
    content: str,
    qa_id: Optional[str] = None,
) -> datetime:
    """Update one documented text field belonging to a job."""
    if content_type not in SUPPORTED_CONTENT_TYPES:
        raise ValueError(f"Unsupported content type: {content_type}")

    if content_type.startswith("qa_"):
        if not qa_id:
            raise ValueError("qa_id is required for Q&A content")
        qa = (
            db.query(QaResult)
            .filter(QaResult.id == qa_id, QaResult.job_id == job.id)
            .first()
        )
        if not qa:
            raise ResultContentNotFound("Q&A result not found")
        if content_type == "qa_question":
            qa.question = content
        else:
            qa.answer = content
    elif content_type == "youtube_transcript":
        if not job.youtube_transcript:
            raise ResultContentNotFound("YouTube transcript not found")
        job.youtube_transcript.text = content
    elif content_type == "transcript":
        if not job.transcript:
            raise ResultContentNotFound("Transcript not found")
        job.transcript.text = content
    elif content_type == "proofread":
        if not job.corrected_transcript:
            raise ResultContentNotFound("Proofread result not found")
        job.corrected_transcript.corrected_text = content
    elif content_type == "key_points":
        if not job.key_points_summary:
            raise ResultContentNotFound("Key-points result not found")
        job.key_points_summary.key_points_text = content
    elif content_type == "note":
        if not job.note:
            from models import JobNote

            job.note = JobNote(job_id=job.id, content=content)
            db.add(job.note)
        else:
            job.note.content = content

    db.commit()
    return datetime.now(timezone.utc)
