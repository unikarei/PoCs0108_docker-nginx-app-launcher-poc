"""
FastAPI application entry point for YouTube Transcription Service
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder

from database import engine, Base
from routers import jobs, export, health, folders, items, tags, notes


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("Starting YouTube Transcription API")
    
    # Database schema is managed by Alembic migrations.
    logger.info("Database schema is managed by Alembic migrations")
    
    yield
    
    # Shutdown
    logger.info("Shutting down YouTube Transcription API")


# Create FastAPI application
app = FastAPI(
    title="YouTube Transcription API",
    description="API for transcribing YouTube videos with OpenAI Whisper and LLM correction",
    version="1.0.0",
    lifespan=lifespan
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle validation errors with structured response
    """
    # Pydantic v2 error contexts can include non-JSON-serializable objects (e.g. ValueError)
    # so ensure we encode errors before returning them.
    encoded_errors = jsonable_encoder(exc.errors())
    logger.warning(f"Validation error: {encoded_errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": encoded_errors,
            "message": "Request validation failed"
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handle uncaught exceptions
    """
    logger.error(f"Unhandled exception: {type(exc).__name__}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "message": str(exc)
        }
    )


# Include routers
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(export.router, prefix="/api/jobs", tags=["export"])
app.include_router(folders.router, prefix="/api/folders", tags=["folders"])
app.include_router(items.router, prefix="/api", tags=["items"])
app.include_router(tags.router, prefix="/api/tags", tags=["tags"])
app.include_router(notes.router, prefix="/api", tags=["notes"])
app.include_router(health.router, tags=["health"])


# Root endpoint
@app.get("/")
async def root():
    """
    Root endpoint
    """
    return {
        "service": "YouTube Transcription API",
        "version": "1.0.0",
        "status": "running"
    }
