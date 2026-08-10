"""
Tag management endpoints
"""
import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Tag, ItemTag
from routers.schemas import TagCreate, TagResponse, TagListResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=TagListResponse)
async def get_tags(db: Annotated[Session, Depends(get_db)]):
    """
    Get all tags
    """
    try:
        tags = db.query(Tag).order_by(Tag.name).all()
        return {"tags": tags}
    except Exception as e:
        logger.error(f"Failed to get tags: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tags",
        )


@router.post("/", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    request: TagCreate,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Create a new tag
    """
    try:
        # Check if tag already exists
        existing_tag = db.query(Tag).filter(Tag.name == request.name).first()
        if existing_tag:
            # Return existing tag instead of error (idempotent)
            return existing_tag
        
        tag = Tag(
            name=request.name,
            color=request.color,
        )
        
        db.add(tag)
        db.commit()
        db.refresh(tag)
        
        return tag
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create tag: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tag",
        )


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: str,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Delete a tag (removes all item associations)
    """
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )
    
    try:
        # Delete tag (cascades to item_tags)
        db.delete(tag)
        db.commit()
        
        return {"tag_id": tag_id, "deleted": True}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete tag: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tag",
        )
