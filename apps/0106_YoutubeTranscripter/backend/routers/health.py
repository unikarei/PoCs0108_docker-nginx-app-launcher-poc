"""
Health check and monitoring endpoints
"""
import logging
from datetime import datetime

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from kombu.exceptions import OperationalError as KombuOperationalError

from database import engine
from routers.schemas import HealthResponse
from worker import celery_app

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    
    Checks:
    - Database connection
    - Redis connection (via Celery)
    
    Returns:
        Health status
    """
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown",
        "timestamp": datetime.utcnow()
    }
    
    # Check database
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["database"] = "healthy"
        logger.debug("Database health check: OK")
    except Exception as e:
        health_status["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
        logger.error(f"Database health check failed: {e}")
    
    # Check Redis broker connectivity and worker availability.
    try:
        with celery_app.connection_or_acquire() as conn:
            conn.ensure_connection(max_retries=1)

        inspector = celery_app.control.inspect(timeout=1)
        ping = inspector.ping() if inspector else None
        if ping:
            health_status["redis"] = f"healthy (workers={len(ping)})"
            logger.debug("Redis/Celery health check: broker and worker OK")
        else:
            health_status["redis"] = "degraded: broker reachable but no active Celery worker"
            health_status["status"] = "degraded"
            logger.warning("Redis broker reachable but no Celery workers responded")
    except KombuOperationalError as e:
        health_status["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
        logger.error(f"Redis broker health check failed: {e}")
    except Exception as e:
        health_status["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"
        logger.error(f"Redis/Celery health check failed: {e}")
    
    # Determine HTTP status code
    if health_status["status"] == "healthy":
        status_code = status.HTTP_200_OK
    else:
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": health_status["status"],
            "database": health_status["database"],
            "redis": health_status["redis"],
            "timestamp": health_status["timestamp"].isoformat()
        }
    )
