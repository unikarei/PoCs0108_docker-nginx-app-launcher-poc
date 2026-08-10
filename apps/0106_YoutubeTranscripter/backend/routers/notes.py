"""
Note management endpoints for jobs
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import Job, JobNote

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Pydantic Schemas
# ============================================================================

class NoteResponse(BaseModel):
    """Response schema for job note"""
    job_id: str
    content: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class UpdateNoteRequest(BaseModel):
    """Request schema for updating job note"""
    content: str = Field(..., description="Note content")


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/jobs/{job_id}/note", response_model=NoteResponse)
async def get_note(job_id: str, db: Session = Depends(get_db)):
    """
    Get note for a specific job
    """
    # Verify job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Get note
    note = db.query(JobNote).filter(JobNote.job_id == job_id).first()
    
    if note:
        return NoteResponse(
            job_id=job_id,
            content=note.content,
            created_at=note.created_at.isoformat() if note.created_at else None,
            updated_at=note.updated_at.isoformat() if note.updated_at else None
        )
    else:
        return NoteResponse(
            job_id=job_id,
            content=None,
            created_at=None,
            updated_at=None
        )


@router.put("/jobs/{job_id}/note", response_model=NoteResponse)
async def update_note(job_id: str, request: UpdateNoteRequest, db: Session = Depends(get_db)):
    """
    Create or update note for a specific job (upsert)
    """
    # Verify job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    # Get existing note or create new one
    note = db.query(JobNote).filter(JobNote.job_id == job_id).first()
    
    if note:
        # Update existing note
        note.content = request.content
        logger.info(f"Updated note for job {job_id}")
    else:
        # Create new note
        note = JobNote(
            job_id=job_id,
            content=request.content
        )
        db.add(note)
        logger.info(f"Created note for job {job_id}")
    
    db.commit()
    db.refresh(note)
    
    return NoteResponse(
        job_id=job_id,
        content=note.content,
        created_at=note.created_at.isoformat() if note.created_at else None,
        updated_at=note.updated_at.isoformat() if note.updated_at else None
    )
