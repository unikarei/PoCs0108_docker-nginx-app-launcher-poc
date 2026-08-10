"""
Item management API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from datetime import datetime

from database import get_db
from models import Item, Folder, Job, ItemTag, Tag
from routers.schemas import (
    ItemResponse, ItemListResponse, ItemMoveRequest, TagInfo,
    ItemTagRequest, BulkMoveRequest, BulkTagRequest, BulkDeleteRequest,
    BulkOperationResult, ItemRatingUpdate
)

router = APIRouter()


def _item_to_response(item: Item, db: Session) -> ItemResponse:
    """
    Convert Item model to ItemResponse schema
    """
    # Get tags for this item
    tags = (
        db.query(Tag)
        .join(ItemTag, ItemTag.tag_id == Tag.id)
        .filter(ItemTag.item_id == item.id)
        .all()
    )
    
    tag_infos = [
        TagInfo(id=tag.id, name=tag.name, color=tag.color)
        for tag in tags
    ]
    
    # Get job info for status/progress
    job = db.query(Job).filter(Job.id == item.job_id).first()
    
    return ItemResponse(
        id=item.id,
        folder_id=item.folder_id,
        job_id=item.job_id,
        title=item.title or (job.user_title if job else None),
        youtube_url=item.youtube_url or (job.youtube_url if job else None),
        status=item.status,
        progress=item.progress,
        duration_seconds=item.duration_seconds,
        cost_usd=float(item.cost_usd) if item.cost_usd else None,
        rating=item.rating,
        tags=tag_infos,
        created_at=item.created_at,
        updated_at=item.updated_at
    )


@router.get("/folders/{folder_id}/items", response_model=ItemListResponse)
async def get_folder_items(
    folder_id: str,
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Keyword search"),
    tag: Optional[str] = Query(None, description="Tag filter"),
    status: Optional[str] = Query(None, description="Status filter"),
    sort: Optional[str] = Query("created_at", description="Sort by field"),
    order: Optional[str] = Query("desc", description="Sort order (asc/desc)"),
    limit: Optional[int] = Query(50, ge=1, le=500),
    offset: Optional[int] = Query(0, ge=0)
):
    """
    Get items in a folder with filtering and sorting
    """
    # Verify folder exists
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    # Build query
    query = db.query(Item).filter(Item.folder_id == folder_id)
    
    # Apply keyword search
    if q:
        query = query.filter(
            or_(
                Item.title.ilike(f"%{q}%"),
                Item.youtube_url.ilike(f"%{q}%")
            )
        )
    
    # Apply tag filter
    if tag:
        query = query.join(ItemTag).join(Tag).filter(Tag.name == tag)
    
    # Apply status filter
    if status:
        query = query.filter(Item.status == status)
    
    # Get total count before pagination
    total = query.count()
    
    # Apply sorting
    if sort == "rating":
        sort_column = func.coalesce(Item.rating, 0)
    else:
        sort_column = getattr(Item, sort, Item.created_at)
    if order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    # Execute query
    items = query.all()
    
    # Convert to response schema
    item_responses = [_item_to_response(item, db) for item in items]
    
    return ItemListResponse(items=item_responses, total=total)


@router.get("/items/search", response_model=ItemListResponse)
async def search_items(
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Keyword search"),
    tag: Optional[str] = Query(None, description="Tag filter"),
    status: Optional[str] = Query(None, description="Status filter"),
    folder_id: Optional[str] = Query(None, description="Folder filter"),
    sort: Optional[str] = Query("created_at", description="Sort by field"),
    order: Optional[str] = Query("desc", description="Sort order (asc/desc)"),
    limit: Optional[int] = Query(50, ge=1, le=500),
    offset: Optional[int] = Query(0, ge=0)
):
    """
    Global search across all folders
    """
    # Build query
    query = db.query(Item)
    
    # Apply folder filter
    if folder_id:
        query = query.filter(Item.folder_id == folder_id)
    
    # Apply keyword search
    if q:
        query = query.filter(
            or_(
                Item.title.ilike(f"%{q}%"),
                Item.youtube_url.ilike(f"%{q}%")
            )
        )
    
    # Apply tag filter
    if tag:
        query = query.join(ItemTag).join(Tag).filter(Tag.name == tag)
    
    # Apply status filter
    if status:
        query = query.filter(Item.status == status)
    
    # Get total count before pagination
    total = query.count()
    
    # Apply sorting
    sort_column = getattr(Item, sort, Item.created_at)
    if order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    # Execute query
    items = query.all()
    
    # Convert to response schema
    item_responses = [_item_to_response(item, db) for item in items]
    
    return ItemListResponse(items=item_responses, total=total)


# Bulk operations (must be before {item_id} routes to avoid path conflicts)
@router.post("/items/bulk/move", response_model=BulkOperationResult)
async def bulk_move_items(
    bulk_request: BulkMoveRequest,
    db: Session = Depends(get_db)
):
    """
    Move multiple items to a target folder
    """
    # Verify target folder exists
    target_folder = db.query(Folder).filter(Folder.id == bulk_request.target_folder_id).first()
    if not target_folder:
        raise HTTPException(status_code=404, detail="Target folder not found")
    
    success_count = 0
    failed_count = 0
    failed_items = []
    
    for item_id in bulk_request.item_ids:
        try:
            item = db.query(Item).filter(Item.id == item_id).first()
            if not item:
                failed_count += 1
                failed_items.append({"item_id": item_id, "error": "Item not found"})
                continue
            
            item.folder_id = bulk_request.target_folder_id
            item.updated_at = datetime.utcnow()
            success_count += 1
            
        except Exception as e:
            failed_count += 1
            failed_items.append({"item_id": item_id, "error": str(e)})
    
    db.commit()
    
    return BulkOperationResult(
        success_count=success_count,
        failed_count=failed_count,
        failed_items=failed_items
    )


@router.post("/items/bulk/tag", response_model=BulkOperationResult)
async def bulk_tag_items(
    bulk_request: BulkTagRequest,
    db: Session = Depends(get_db)
):
    """
    Add a tag to multiple items
    """
    # Get or create tag
    tag = db.query(Tag).filter(Tag.name == bulk_request.tag_name).first()
    if not tag:
        tag = Tag(name=bulk_request.tag_name)
        db.add(tag)
        db.flush()
    
    success_count = 0
    failed_count = 0
    failed_items = []
    
    for item_id in bulk_request.item_ids:
        try:
            item = db.query(Item).filter(Item.id == item_id).first()
            if not item:
                failed_count += 1
                failed_items.append({"item_id": item_id, "error": "Item not found"})
                continue
            
            # Check if tag already associated
            existing = db.query(ItemTag).filter(
                ItemTag.item_id == item_id,
                ItemTag.tag_id == tag.id
            ).first()
            
            if not existing:
                item_tag = ItemTag(item_id=item_id, tag_id=tag.id)
                db.add(item_tag)
            
            success_count += 1
            
        except Exception as e:
            failed_count += 1
            failed_items.append({"item_id": item_id, "error": str(e)})
    
    db.commit()
    
    return BulkOperationResult(
        success_count=success_count,
        failed_count=failed_count,
        failed_items=failed_items
    )


@router.post("/items/bulk/delete", response_model=BulkOperationResult)
async def bulk_delete_items(
    bulk_request: BulkDeleteRequest,
    db: Session = Depends(get_db)
):
    """
    Delete multiple items
    """
    success_count = 0
    failed_count = 0
    failed_items = []
    
    for item_id in bulk_request.item_ids:
        try:
            item = db.query(Item).filter(Item.id == item_id).first()
            if not item:
                failed_count += 1
                failed_items.append({"item_id": item_id, "error": "Item not found"})
                continue
            
            db.delete(item)
            success_count += 1
            
        except Exception as e:
            failed_count += 1
            failed_items.append({"item_id": item_id, "error": str(e)})
    
    db.commit()
    
    return BulkOperationResult(
        success_count=success_count,
        failed_count=failed_count,
        failed_items=failed_items
    )


# Item-specific operations (must be after bulk operations)
@router.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: str,
    db: Session = Depends(get_db)
):
    """
    Get item details
    """
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return _item_to_response(item, db)


@router.post("/items/{item_id}/move")
async def move_item(
    item_id: str,
    move_request: ItemMoveRequest,
    db: Session = Depends(get_db)
):
    """
    Move an item to a different folder
    """
    # Verify item exists
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Verify target folder exists
    target_folder = db.query(Folder).filter(Folder.id == move_request.target_folder_id).first()
    if not target_folder:
        raise HTTPException(status_code=404, detail="Target folder not found")
    
    # Move item
    item.folder_id = move_request.target_folder_id
    item.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(item)
    
    return {
        "status": "success",
        "message": f"Item moved to folder '{target_folder.name}'",
        "item": _item_to_response(item, db)
    }


@router.patch("/items/{item_id}/rating", response_model=ItemResponse)
async def update_item_rating(
    item_id: str,
    request: ItemRatingUpdate,
    db: Session = Depends(get_db),
):
    """Update item rating from 1 to 5 stars."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    item.rating = request.rating
    item.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)

    return _item_to_response(item, db)


@router.delete("/items/{item_id}")
async def delete_item(
    item_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete an item (and optionally its associated job)
    """
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Store job_id before deletion
    job_id = item.job_id
    
    # Delete item (cascades to artifacts and item_tags)
    db.delete(item)
    db.commit()
    
    return {
        "status": "success",
        "message": f"Item deleted successfully",
        "item_id": item_id,
        "job_id": job_id
    }


def sync_item_status_from_job(db: Session, job_id: str):
    """
    Sync Item status from Job status
    Called when Job status is updated
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return
    
    item = db.query(Item).filter(Item.job_id == job_id).first()
    if not item:
        return
    
    # Map Job status to Item status
    status_map = {
        'pending': 'queued',
        'processing': 'running',
        'transcribing': 'running',
        'correcting': 'running',
        'completed': 'completed',
        'failed': 'failed'
    }
    
    new_status = status_map.get(job.status, 'queued')
    
    if item.status != new_status:
        item.status = new_status
        item.progress = job.progress
        item.updated_at = datetime.utcnow()
        db.commit()


@router.post("/items/{item_id}/tags")
async def add_tag_to_item(
    item_id: str,
    tag_request: ItemTagRequest,
    db: Session = Depends(get_db)
):
    """
    Add a tag to an item
    """
    # Verify item exists
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Get or create tag
    tag = db.query(Tag).filter(Tag.name == tag_request.tag_name).first()
    if not tag:
        tag = Tag(name=tag_request.tag_name)
        db.add(tag)
        db.flush()
    
    # Check if tag already associated
    existing = db.query(ItemTag).filter(
        ItemTag.item_id == item_id,
        ItemTag.tag_id == tag.id
    ).first()
    
    if not existing:
        item_tag = ItemTag(item_id=item_id, tag_id=tag.id)
        db.add(item_tag)
        db.commit()
    
    return {
        "status": "success",
        "message": f"Tag '{tag_request.tag_name}' added to item",
        "tag": TagInfo(id=tag.id, name=tag.name, color=tag.color)
    }


@router.delete("/items/{item_id}/tags/{tag_id}")
async def remove_tag_from_item(
    item_id: str,
    tag_id: str,
    db: Session = Depends(get_db)
):
    """
    Remove a tag from an item
    """
    # Verify item exists
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Find item_tag association
    item_tag = db.query(ItemTag).filter(
        ItemTag.item_id == item_id,
        ItemTag.tag_id == tag_id
    ).first()
    
    if not item_tag:
        raise HTTPException(status_code=404, detail="Tag not associated with this item")
    
    db.delete(item_tag)
    db.commit()
    
    return {
        "status": "success",
        "message": "Tag removed from item"
    }

