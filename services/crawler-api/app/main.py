"""
Main FastAPI application for the crawler API service.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
import structlog
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
import uvicorn
import sys
import os

# Add the parent directory to the path so we can import shared modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from app.core.config import settings
from app.core.database import engine, create_tables
from app.core.logging import setup_logging
from app.api.v1 import crawler, health
from app.utils.metrics import setup_metrics
from shared.models import ErrorResponse

# Setup logging
setup_logging()
logger = structlog.get_logger()

# Setup Sentry for error tracking
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            FastApiIntegration(auto_enable=True),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,
        environment=settings.ENVIRONMENT,
    )

# Create FastAPI app
app = FastAPI(
    title="BrightEdge Crawler API",
    description="Production-grade web crawler service for metadata extraction and content classification",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Setup metrics
setup_metrics(app)

# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include routers
app.include_router(
    health.router,
    prefix="/health",
    tags=["health"]
)

app.include_router(
    crawler.router,
    prefix="/api/v1",
    tags=["crawler"]
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with correlation ID."""
    import uuid
    import time
    
    # Generate correlation ID
    correlation_id = str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    
    # Log request
    start_time = time.time()
    logger.info(
        "request_started",
        method=request.method,
        url=str(request.url),
        correlation_id=correlation_id,
        client_ip=request.client.host if request.client else None,
    )
    
    # Process request
    try:
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(
            "request_completed",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            process_time=process_time,
            correlation_id=correlation_id,
        )
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        return response
        
    except Exception as e:
        # Log error
        process_time = time.time() - start_time
        logger.error(
            "request_failed",
            method=request.method,
            url=str(request.url),
            error=str(e),
            process_time=process_time,
            correlation_id=correlation_id,
        )
        raise


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    correlation_id = getattr(request.state, 'correlation_id', None)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.__class__.__name__,
            message=exc.detail,
            request_id=correlation_id,
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    correlation_id = getattr(request.state, 'correlation_id', None)
    
    logger.error(
        "unhandled_exception",
        error=str(exc),
        correlation_id=correlation_id,
        exc_info=True,
    )
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="InternalServerError",
            message="An unexpected error occurred",
            request_id=correlation_id,
        ).dict()
    )


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("application_starting", version="1.0.0")
    
    # Create database tables
    await create_tables()
    
    logger.info("application_started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("application_shutdown")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level="info",
    )
