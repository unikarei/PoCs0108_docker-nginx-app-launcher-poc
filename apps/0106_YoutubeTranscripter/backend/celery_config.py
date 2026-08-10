"""
Celery configuration for YouTube Transcription App
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Celery Broker and Result Backend
_default_redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
broker_url = os.getenv("CELERY_BROKER_URL", _default_redis_url)
result_backend = os.getenv("CELERY_RESULT_BACKEND", _default_redis_url)

# Task Serialization
task_serializer = "json"
accept_content = ["json"]
result_serializer = "json"

# Timezone
timezone = "UTC"
enable_utc = True

# Task Execution
task_acks_late = True  # Acknowledge tasks only after completion
task_reject_on_worker_lost = True  # Reject tasks if worker dies

# Task Retry Configuration
task_default_retry_delay = 60  # Retry after 60 seconds
task_max_retries = 3  # Maximum 3 retries

# Worker Configuration
worker_prefetch_multiplier = 1  # Process one task at a time for long-running tasks
worker_max_tasks_per_child = 1000  # Restart worker after 1000 tasks to prevent memory leaks

# Task Time Limits
task_soft_time_limit = 3600  # 1 hour soft limit
task_time_limit = 3900  # 1 hour 5 minutes hard limit

# Task Routes (optional, for future queue separation)
task_routes = {
    "worker.transcription_task": {"queue": "transcription"},
    "worker.correction_task": {"queue": "correction"},
    # These tasks should be consumed by the existing worker queues.
    "worker.proofread_task": {"queue": "correction"},
    "worker.qa_task": {"queue": "correction"},
}

# Result Expiration
result_expires = 86400  # Results expire after 24 hours
