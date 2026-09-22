"""Default Library title generation for YouTube jobs."""

from datetime import datetime
from typing import Any, Mapping, Optional


def build_default_job_title(
    metadata: Optional[Mapping[str, Any]] = None,
    created_at: Optional[datetime] = None,
) -> str:
    """Build the initial title used when a job has no user-provided title."""
    metadata = metadata or {}
    uploader = (
        metadata.get("uploader")
        or metadata.get("channel")
        or metadata.get("creator")
        or "YouTube"
    )
    uploader_name = str(uploader).strip() or "YouTube"
    title_date = created_at or datetime.now()
    return f"【{uploader_name}】YouTube {title_date.year}/{title_date.month}/{title_date.day}"
