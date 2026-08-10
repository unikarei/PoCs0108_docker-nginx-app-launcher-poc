"""
Pydantic schemas for API request/response models
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, validator


class TranscribeJobRequest(BaseModel):
    """
    Request schema for creating a new transcription job
    """
    youtube_url: str = Field(..., description="YouTube video URL")
    user_title: Optional[str] = Field(default=None, description="Optional user-provided title")
    tags: Optional[str] = Field(default=None, description="Optional semicolon-delimited tags (e.g., 'tag1;tag2')")
    language: str = Field(..., description="Target language (ja or en)")
    model: str = Field(default="gpt-4o-mini-transcribe", description="Transcription model")
    
    @validator('youtube_url')
    def validate_youtube_url(cls, v):
        """Validate YouTube URL format"""
        if not v:
            raise ValueError('YouTube URL is required')
        
        valid_domains = ['youtube.com', 'youtu.be', 'www.youtube.com']
        if not any(domain in v.lower() for domain in valid_domains):
            raise ValueError('Invalid YouTube URL')
        
        return v
    
    @validator('language')
    def validate_language(cls, v):
        """Validate language code"""
        if v not in ['ja', 'en']:
            raise ValueError('Language must be "ja" or "en"')
        return v
    
    @validator('model')
    def validate_model(cls, v):
        """Validate transcription model"""
        valid_models = ['gpt-4o-mini-transcribe', 'gpt-4o-transcribe', 'whisper-1']
        if v not in valid_models:
            raise ValueError(f'Model must be one of {valid_models}')
        return v


class TranscribeJobResponse(BaseModel):
    """
    Response schema for job creation
    """
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    """
    Response schema for job status
    """
    job_id: str
    status: str
    stage: Optional[str] = Field(default=None, description="Granular stage (download_extract|preprocess|transcribe|merge|export)")
    stage_detail: Optional[Dict[str, Any]] = Field(default=None, description="Structured stage details (e.g., chunk index/count)")
    progress: int
    youtube_url: str
    user_title: Optional[str] = None
    tags: Optional[str] = None
    language: str
    model: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AudioFileInfo(BaseModel):
    """
    Audio file information
    """
    title: Optional[str] = None
    duration_seconds: Optional[int] = None
    format: Optional[str] = None
    file_size_bytes: Optional[int] = None
    
    class Config:
        from_attributes = True


class TranscriptInfo(BaseModel):
    """
    Transcript information
    """
    text: str
    language_detected: Optional[str] = None
    transcription_model: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class CorrectedTranscriptInfo(BaseModel):
    """
    Corrected transcript information
    """
    corrected_text: str
    original_text: str
    correction_model: Optional[str] = None
    changes_summary: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class JobResultResponse(BaseModel):
    """
    Response schema for job result
    """
    job_id: str
    status: str
    model: Optional[str] = None
    audio_file: Optional[AudioFileInfo] = None
    transcript: Optional[TranscriptInfo] = None
    corrected_transcript: Optional[CorrectedTranscriptInfo] = None
    qa_results: Optional[List["QaResultInfo"]] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True


class CorrectTranscriptRequest(BaseModel):
    """
    Request schema for LLM correction
    """
    correction_model: str = Field(default="gpt-4o-mini", description="LLM model for correction")
    
    @validator('correction_model')
    def validate_correction_model(cls, v):
        """Validate correction model"""
        valid_models = ['gpt-4o-mini', 'gpt-4o']
        if v not in valid_models:
            raise ValueError(f'Correction model must be one of {valid_models}')
        return v


class CorrectTranscriptResponse(BaseModel):
    """
    Response schema for correction request
    """
    job_id: str
    status: str
    message: str


class ProofreadRequest(BaseModel):
    proofread_model: str = Field(default="gpt-4o-mini", description="LLM model for proofreading")

    @validator('proofread_model')
    def validate_proofread_model(cls, v):
        valid_models = ['gpt-4o-mini', 'gpt-4o']
        if v not in valid_models:
            raise ValueError(f'Proofread model must be one of {valid_models}')
        return v


class ProofreadResponse(BaseModel):
    job_id: str
    status: str
    message: str


class QaRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User question for QA")
    qa_model: str = Field(default="gpt-4o-mini", description="LLM model for QA")

    @validator('qa_model')
    def validate_qa_model(cls, v):
        valid_models = ['gpt-4o-mini', 'gpt-4o']
        if v not in valid_models:
            raise ValueError(f'QA model must be one of {valid_models}')
        return v


class QaResponse(BaseModel):
    job_id: str
    status: str
    message: str


class QaResultInfo(BaseModel):
    question: str
    answer: str
    qa_model: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Resolve forward references (Pydantic v1/v2 compatible)
try:
    JobResultResponse.model_rebuild()
except AttributeError:
    JobResultResponse.update_forward_refs()


class HealthResponse(BaseModel):
    """
    Response schema for health check
    """
    status: str
    database: str
    redis: str
    timestamp: datetime


class JobListItem(BaseModel):
    job_id: str
    status: str
    youtube_url: str
    title: Optional[str] = None
    user_title: Optional[str] = None
    tags: Optional[str] = None
    language: str
    model: str
    duration_seconds: Optional[int] = None
    has_qa: bool = False
    created_at: datetime
    updated_at: datetime


class JobListResponse(BaseModel):
    items: List[JobListItem]
    total: int


class ExpandRequest(BaseModel):
    url: str = Field(..., description="Playlist or channel URL")


class ExpandItem(BaseModel):
    youtube_url: str
    title: Optional[str] = None


class ExpandResponse(BaseModel):
    items: List[ExpandItem]


class DeleteJobResponse(BaseModel):
    job_id: str
    deleted: bool


class CancelJobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class BulkDeleteJobsRequest(BaseModel):
    job_ids: List[str] = Field(..., min_length=1, description="Job IDs to delete")


class BulkDeleteJobsItemResult(BaseModel):
    job_id: str
    deleted: bool
    reason: Optional[str] = None


class BulkDeleteJobsResponse(BaseModel):
    deleted_count: int
    results: List[BulkDeleteJobsItemResult]


# ============================================================================
# Update Title Schemas
# ============================================================================

class UpdateTitleRequest(BaseModel):
    """Request schema for updating job title"""
    title: str = Field(..., min_length=1, max_length=500, description="New title for the job")


class UpdateTitleResponse(BaseModel):
    """Response schema for title update"""
    job_id: str
    title: str
    message: str


# ============================================================================
# Folder Tree Schemas (New)
# ============================================================================

class FolderSettings(BaseModel):
    """Folder default settings"""
    default_language: Optional[str] = None
    default_model: Optional[str] = None
    default_prompt: Optional[str] = None
    default_qa_enabled: Optional[bool] = False
    default_output_format: Optional[str] = 'txt'
    naming_template: Optional[str] = None


class FolderBase(BaseModel):
    """Base folder schema"""
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class FolderCreate(FolderBase):
    """Schema for creating a folder"""
    default_language: Optional[str] = None
    default_model: Optional[str] = None
    default_prompt: Optional[str] = None
    default_qa_enabled: Optional[bool] = False
    default_output_format: Optional[str] = 'txt'
    naming_template: Optional[str] = None


class FolderUpdate(BaseModel):
    """Schema for updating a folder"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class FolderItemCount(BaseModel):
    """Item count by status"""
    queued: int = 0
    running: int = 0
    completed: int = 0
    failed: int = 0


class FolderResponse(FolderBase):
    """Schema for folder response"""
    id: str
    path: str
    default_language: Optional[str] = None
    default_model: Optional[str] = None
    default_prompt: Optional[str] = None
    default_qa_enabled: Optional[bool] = False
    default_output_format: Optional[str] = 'txt'
    naming_template: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    item_count: Optional[FolderItemCount] = None
    children: Optional[List['FolderResponse']] = []

    class Config:
        from_attributes = True


# For recursive type
FolderResponse.model_rebuild()


class FolderTreeResponse(BaseModel):
    """Schema for folder tree response"""
    folders: List[FolderResponse]


class FolderSettingsResponse(FolderSettings):
    """Schema for folder settings response"""
    folder_id: str
    folder_name: str
    
    class Config:
        from_attributes = True


# =============================================================================
# Item Schemas
# =============================================================================

class ItemBase(BaseModel):
    """Base schema for Item"""
    title: Optional[str] = None
    youtube_url: Optional[str] = None


class ItemCreate(ItemBase):
    """Schema for creating an item"""
    folder_id: str
    job_id: str


class ItemUpdate(BaseModel):
    """Schema for updating an item"""
    title: Optional[str] = None
    folder_id: Optional[str] = None


class ItemMoveRequest(BaseModel):
    """Schema for moving an item to another folder"""
    target_folder_id: str


class TagInfo(BaseModel):
    """Schema for tag information"""
    id: str
    name: str
    color: Optional[str] = None
    
    class Config:
        from_attributes = True


class ItemResponse(BaseModel):
    """Schema for item response"""
    id: str
    folder_id: str
    job_id: str
    title: Optional[str] = None
    youtube_url: Optional[str] = None
    status: str
    progress: Optional[int] = None
    duration_seconds: Optional[int] = None
    cost_usd: Optional[float] = None
    rating: Optional[int] = None
    tags: List[TagInfo] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ItemListResponse(BaseModel):
    """Schema for item list response"""
    items: List[ItemResponse]
    total: int


class ItemRatingUpdate(BaseModel):
    """Schema for updating an item's rating"""
    rating: int = Field(..., ge=1, le=5)


# Tag Schemas
class TagCreate(BaseModel):
    """Schema for creating a tag"""
    name: str = Field(..., max_length=100)
    color: Optional[str] = Field(None, max_length=20)


class TagResponse(BaseModel):
    """Schema for tag response"""
    id: str
    name: str
    color: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class TagListResponse(BaseModel):
    """Schema for tag list response"""
    tags: List[TagResponse]


# Bulk Operation Schemas
class BulkMoveRequest(BaseModel):
    """Schema for bulk move operation"""
    item_ids: List[str] = Field(..., min_items=1)
    target_folder_id: str


class BulkTagRequest(BaseModel):
    """Schema for bulk tag operation"""
    item_ids: List[str] = Field(..., min_items=1)
    tag_name: str


class BulkDeleteRequest(BaseModel):
    """Schema for bulk delete operation"""
    item_ids: List[str] = Field(..., min_items=1)


class BulkOperationResult(BaseModel):
    """Schema for bulk operation result"""
    success_count: int
    failed_count: int
    failed_items: List[Dict[str, str]] = []  # [{"item_id": "...", "error": "..."}]


class ItemTagRequest(BaseModel):
    """Schema for adding a tag to an item"""
    tag_name: str

