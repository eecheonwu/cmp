"""
CMP FastAPI Application Entry Point.

Main application module with:
- FastAPI app initialization with async lifespan
- CORS middleware for CloudFront domain
- Correlation ID middleware for request tracing
- Health check endpoint
- Router registration structure
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.config import settings
from db.session import close_db, init_db
from api.v1.auth.router import router as auth_router
from api.v1.appointments.router import router as appointments_router
from api.v1.clinical_records.router import router as clinical_records_router
from api.v1.reports.router import router as reports_router
from api.v1.admin.router import router as admin_router

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(message)s" if settings.LOG_FORMAT == "json" else None,
)
logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation ID to each request for distributed tracing.

    The correlation ID is:
    - Read from X-Correlation-ID header if present
    - Generated as new UUID if not present
    - Added to response headers
    - Available in request.state for logging
    """

    async def dispatch(self, request: Request, call_next):
        # Get or generate correlation ID
        correlation_id = request.headers.get(
            settings.CORRELATION_ID_HEADER, str(uuid.uuid4())
        )

        # Store in request state for access in route handlers
        request.state.correlation_id = correlation_id

        # Add to response headers
        response = await call_next(request)
        response.headers[settings.CORRELATION_ID_HEADER] = correlation_id

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured request/response logging with timing.
    """

    async def dispatch(self, request: Request, call_next):
        # Start timer
        start_time = time.time()

        # Get correlation ID
        correlation_id = getattr(request.state, "correlation_id", "N/A")

        # Log request
        logger.info(
            {
                "event": "request_started",
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_host": request.client.host if request.client else None,
            }
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            logger.info(
                {
                    "event": "request_completed",
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_seconds": round(duration, 4),
                }
            )

            return response

        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time

            # Log error
            logger.error(
                {
                    "event": "request_failed",
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "duration_seconds": round(duration, 4),
                }
            )

            # Re-raise to let FastAPI handle it
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events:
    - Startup: Initialize database connection pool
    - Shutdown: Close database connections
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

    # Initialize database (only in dev/test)
    if settings.is_development:
        logger.info("Initializing database tables (development mode)")
        await init_db()

    yield

    # Shutdown
    logger.info("Shutting down application")
    await close_db()


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for Clinic Modernization Platform",
    version=settings.APP_VERSION,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=[settings.CORRELATION_ID_HEADER],  # Expose correlation ID
)

# Add custom middleware (order matters: last added = first executed)
app.add_middleware(LoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns:
        JSONResponse: Health status of the application
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "application": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        },
    )


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information.

    Returns:
        JSONResponse: API information
    """
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


# Include API routers
app.include_router(auth_router, prefix=settings.API_V1_PREFIX, tags=["auth"])
app.include_router(appointments_router, prefix=settings.API_V1_PREFIX, tags=["appointments"])
app.include_router(clinical_records_router, prefix=settings.API_V1_PREFIX, tags=["clinical-records"])
app.include_router(reports_router, prefix=settings.API_V1_PREFIX, tags=["reports"])
app.include_router(admin_router, prefix=settings.API_V1_PREFIX, tags=["admin"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
