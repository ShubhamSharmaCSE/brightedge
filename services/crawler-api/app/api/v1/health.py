"""
Health check endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.cache import get_cache, CacheManager
from shared.models import HealthCheck
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.get("/", response_model=HealthCheck)
async def health_check(
    db: AsyncSession = Depends(get_db),
    cache: CacheManager = Depends(get_cache),
):
    """
    Health check endpoint.
    
    Returns the health status of the application and its dependencies.
    """
    health_status = HealthCheck(
        status="healthy",
        version="1.0.0",
        database=False,
        redis=False,
        queue=False,
    )
    
    # Check database connection
    try:
        await db.execute("SELECT 1")
        health_status.database = True
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        health_status.database = False
        health_status.status = "unhealthy"
    
    # Check Redis connection
    try:
        if cache.redis_client:
            await cache.redis_client.ping()
            health_status.redis = True
        else:
            health_status.redis = False
            health_status.status = "degraded"
    except Exception as e:
        logger.error("redis_health_check_failed", error=str(e))
        health_status.redis = False
        health_status.status = "degraded"
    
    # For now, assume queue is healthy if we can connect to Redis
    health_status.queue = health_status.redis
    
    return health_status


@router.get("/liveness")
async def liveness_check():
    """
    Kubernetes liveness probe endpoint.
    
    Returns 200 OK if the application is running.
    """
    return {"status": "alive"}


@router.get("/readiness")
async def readiness_check(
    db: AsyncSession = Depends(get_db),
):
    """
    Kubernetes readiness probe endpoint.
    
    Returns 200 OK if the application is ready to serve requests.
    """
    try:
        # Check if database is accessible
        await db.execute("SELECT 1")
        return {"status": "ready"}
    except Exception as e:
        logger.error("readiness_check_failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service not ready")
