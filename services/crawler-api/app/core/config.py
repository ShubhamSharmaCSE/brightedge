"""
Configuration management for the crawler API service.
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings."""
    
    # App settings
    APP_NAME: str = "BrightEdge Crawler API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database settings
    DATABASE_URL: str = "postgresql://crawler:password@localhost:5432/brightedge"
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis settings
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_CACHE_TTL: int = 3600  # 1 hour
    
    # AWS settings
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_SQS_QUEUE_URL: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    
    # Crawler settings
    DEFAULT_USER_AGENT: str = "BrightEdge-Crawler/1.0 (+https://github.com/ShubhamSharmaCSE/brightedge)"
    MAX_CONCURRENT_REQUESTS: int = 100
    DEFAULT_CRAWL_DELAY: float = 1.0
    MAX_RETRY_ATTEMPTS: int = 3
    REQUEST_TIMEOUT: int = 30
    MAX_CONTENT_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 100
    RATE_LIMIT_BURST_SIZE: int = 10
    
    # Security settings
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    SECRET_KEY: str = "your-secret-key-here"
    
    # Monitoring settings
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    
    # Content classification settings
    ENABLE_TOPIC_CLASSIFICATION: bool = True
    MIN_TOPIC_CONFIDENCE: float = 0.5
    MAX_TOPICS_PER_PAGE: int = 10
    
    # Robots.txt settings
    RESPECT_ROBOTS_TXT: bool = True
    ROBOTS_TXT_CACHE_TTL: int = 86400  # 24 hours
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()


def get_database_url() -> str:
    """Get database URL with proper formatting."""
    return settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")


def get_redis_url() -> str:
    """Get Redis URL."""
    return settings.REDIS_URL


def is_production() -> bool:
    """Check if running in production."""
    return settings.ENVIRONMENT.lower() == "production"


def is_development() -> bool:
    """Check if running in development."""
    return settings.ENVIRONMENT.lower() == "development"
