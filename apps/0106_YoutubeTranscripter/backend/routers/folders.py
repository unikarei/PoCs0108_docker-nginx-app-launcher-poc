"""
Folder management endpoints
"""
import logging
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import Folder, Item
from routers.schemas import (
    FolderCreate,
    FolderUpdate,
    FolderResponse,
    FolderTreeResponse,
    FolderSettings,
    FolderSettingsResponse,
    FolderItemCount,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_folder_path(db: Session, parent_id: Optional[str], folder_name: str) -> str:
    """Build materialized path for folder"""
    if not parent_id:
        return f"/{folder_name}"
    
    parent = db.query(Folder).filter(Folder.id == parent_id).first()
    if not parent:
        raise ValueError("Parent folder not found")
    
    return f"{parent.path}/{folder_name}"


def _get_item_count(db: Session, folder_id: str) -> FolderItemCount:
    """Get item count by status for a folder"""
    counts = (
        db.query(Item.status, func.count(Item.id))
        .filter(Item.folder_id == folder_id)
        .group_by(Item.status)
        .all()
    )
    
    count_dict = {status: count for status, count in counts}
    return FolderItemCount(
        queued=count_dict.get('queued', 0),
        running=count_dict.get('running', 0),
        completed=count_dict.get('completed', 0),
        failed=count_dict.get('failed', 0),
    )


def _build_folder_tree(db: Session, folders: list, parent_id: Optional[str] = None) -> list:
    """Recursively build folder tree with children"""
    result = []
    for folder in [f for f in folders if f.parent_id == parent_id]:
        folder_dict = {
            "id": folder.id,
            "name": folder.name,
            "parent_id": folder.parent_id,
            "path": folder.path,
            "description": folder.description,
            "color": folder.color,
            "icon": folder.icon,
            "default_language": folder.default_language,
            "default_model": folder.default_model,
            "default_prompt": folder.default_prompt,
            "default_qa_enabled": folder.default_qa_enabled,
            "default_output_format": folder.default_output_format,
            "naming_template": folder.naming_template,
            "created_at": folder.created_at,
            "updated_at": folder.updated_at,
            "item_count": _get_item_count(db, folder.id),
            "children": _build_folder_tree(db, folders, folder.id),
        }
        result.append(folder_dict)
    return result


@router.get("/tree", response_model=FolderTreeResponse)
async def get_folder_tree(db: Annotated[Session, Depends(get_db)]):
    """
    Get complete folder tree with item counts
    """
    try:
        all_folders = db.query(Folder).order_by(Folder.path).all()
        tree = _build_folder_tree(db, all_folders, parent_id=None)
        return {"folders": tree}
    except Exception as e:
        logger.error(f"Failed to get folder tree: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get folder tree",
        )


@router.post("/", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    request: FolderCreate,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Create a new folder
    """
    try:
        # Build path
        path = _build_folder_path(db, request.parent_id, request.name)
        
        # Check for duplicate name in same parent
        existing = db.query(Folder).filter(
            Folder.name == request.name,
            Folder.parent_id == request.parent_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Folder with this name already exists in the same parent",
            )
        
        folder = Folder(
            name=request.name,
            parent_id=request.parent_id,
            path=path,
            description=request.description,
            color=request.color,
            icon=request.icon,
            default_language=request.default_language,
            default_model=request.default_model,
            default_prompt=request.default_prompt,
            default_qa_enabled=request.default_qa_enabled,
            default_output_format=request.default_output_format,
            naming_template=request.naming_template,
        )
        
        db.add(folder)
        db.commit()
        db.refresh(folder)
        
        # Add item count
        item_count = _get_item_count(db, folder.id)
        folder_dict = folder.__dict__.copy()
        folder_dict['item_count'] = item_count
        folder_dict['children'] = []
        
        return folder_dict
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create folder: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create folder",
        )


@router.get("/{folder_id}", response_model=FolderResponse)
async def get_folder(
    folder_id: str,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Get folder by ID
    """
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found",
        )
    
    item_count = _get_item_count(db, folder.id)
    folder_dict = folder.__dict__.copy()
    folder_dict['item_count'] = item_count
    folder_dict['children'] = []
    
    return folder_dict


@router.put("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: str,
    request: FolderUpdate,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Update folder
    """
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found",
        )
    
    try:
        # Update fields
        if request.name is not None:
            # Check for duplicate name
            existing = db.query(Folder).filter(
                Folder.name == request.name,
                Folder.parent_id == folder.parent_id,
                Folder.id != folder_id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Folder with this name already exists in the same parent",
                )
            
            # Update path for this folder and all descendants
            old_path = folder.path
            folder.name = request.name
            new_path = _build_folder_path(db, folder.parent_id, folder.name)
            folder.path = new_path
            
            # Update descendant paths
            descendants = db.query(Folder).filter(Folder.path.like(f"{old_path}/%")).all()
            for desc in descendants:
                desc.path = desc.path.replace(old_path, new_path, 1)
        
        if request.description is not None:
            folder.description = request.description
        if request.color is not None:
            folder.color = request.color
        if request.icon is not None:
            folder.icon = request.icon
        
        db.commit()
        db.refresh(folder)
        
        item_count = _get_item_count(db, folder.id)
        folder_dict = folder.__dict__.copy()
        folder_dict['item_count'] = item_count
        folder_dict['children'] = []
        
        return folder_dict
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update folder: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update folder",
        )


@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: str,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Delete folder (only if empty)
    """
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found",
        )
    
    # Check if folder has items
    item_count = db.query(func.count(Item.id)).filter(Item.folder_id == folder_id).scalar()
    if item_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Folder contains {item_count} items. Cannot delete non-empty folder.",
        )
    
    # Check if folder has children
    child_count = db.query(func.count(Folder.id)).filter(Folder.parent_id == folder_id).scalar()
    if child_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Folder contains {child_count} sub-folders. Cannot delete folder with children.",
        )
    
    try:
        db.delete(folder)
        db.commit()
        return {"folder_id": folder_id, "deleted": True}
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete folder: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete folder",
        )


@router.get("/{folder_id}/settings", response_model=FolderSettingsResponse)
async def get_folder_settings(
    folder_id: str,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Get folder settings
    """
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found",
        )
    
    return {
        "folder_id": folder.id,
        "folder_name": folder.name,
        "default_language": folder.default_language,
        "default_model": folder.default_model,
        "default_prompt": folder.default_prompt,
        "default_qa_enabled": folder.default_qa_enabled,
        "default_output_format": folder.default_output_format,
        "naming_template": folder.naming_template,
    }


@router.put("/{folder_id}/settings", response_model=FolderSettingsResponse)
async def update_folder_settings(
    folder_id: str,
    request: FolderSettings,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Update folder settings
    """
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Folder not found",
        )
    
    try:
        if request.default_language is not None:
            folder.default_language = request.default_language
        if request.default_model is not None:
            folder.default_model = request.default_model
        if request.default_prompt is not None:
            folder.default_prompt = request.default_prompt
        if request.default_qa_enabled is not None:
            folder.default_qa_enabled = request.default_qa_enabled
        if request.default_output_format is not None:
            folder.default_output_format = request.default_output_format
        if request.naming_template is not None:
            folder.naming_template = request.naming_template
        
        db.commit()
        db.refresh(folder)
        
        return {
            "folder_id": folder.id,
            "folder_name": folder.name,
            "default_language": folder.default_language,
            "default_model": folder.default_model,
            "default_prompt": folder.default_prompt,
            "default_qa_enabled": folder.default_qa_enabled,
            "default_output_format": folder.default_output_format,
            "naming_template": folder.naming_template,
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update folder settings: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update folder settings",
        )
