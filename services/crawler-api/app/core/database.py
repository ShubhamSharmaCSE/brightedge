"""
Database connection and setup.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Boolean, DECIMAL
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from typing import AsyncGenerator
import uuid

from app.core.config import get_database_url

# Database engine
engine = create_async_engine(
    get_database_url(),
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# Session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base()


class PageMetadataModel(Base):
    """SQLAlchemy model for page metadata."""
    
    __tablename__ = "page_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    crawl_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    url = Column(String(2048), nullable=False, index=True)
    domain = Column(String(255), nullable=False, index=True)
    title = Column(Text)
    description = Column(Text)
    keywords = Column(JSON, default=[])
    author = Column(String(255))
    published_date = Column(DateTime)
    canonical_url = Column(String(2048))
    language = Column(String(10))
    content_type = Column(String(50), default="text/html")
    word_count = Column(Integer, default=0)
    images = Column(JSON, default=[])
    links = Column(JSON, default=[])
    topics = Column(JSON, default=[])
    headers = Column(JSON, default={})
    content_hash = Column(String(64), index=True)
    response_time_ms = Column(Integer, default=0)
    status_code = Column(Integer)
    crawl_timestamp = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CrawlQueueModel(Base):
    """SQLAlchemy model for crawl queue."""
    
    __tablename__ = "crawl_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    crawl_id = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True)
    url = Column(String(2048), nullable=False)
    domain = Column(String(255), nullable=False, index=True)
    priority = Column(Integer, default=5, index=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    crawl_delay = Column(DECIMAL(5, 2), default=1.0)
    respect_robots_txt = Column(Boolean, default=True)
    user_agent = Column(String(255))
    headers = Column(JSON, default={})
    scheduled_at = Column(DateTime, default=datetime.utcnow)
    processing_started_at = Column(DateTime)
    completed_at = Column(DateTime)
    status = Column(String(20), default="pending", index=True)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CrawlHistoryModel(Base):
    """SQLAlchemy model for crawl history."""
    
    __tablename__ = "crawl_history"
    
    id = Column(Integer, primary_key=True, index=True)
    crawl_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    url = Column(String(2048), nullable=False)
    domain = Column(String(255), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    status_code = Column(Integer)
    response_time_ms = Column(Integer)
    error_message = Column(Text)
    crawl_timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class DomainRateLimitModel(Base):
    """SQLAlchemy model for domain rate limits."""
    
    __tablename__ = "domain_rate_limits"
    
    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(255), nullable=False, unique=True, index=True)
    crawl_delay = Column(DECIMAL(5, 2), default=1.0)
    max_concurrent = Column(Integer, default=1)
    robots_txt_url = Column(String(2048))
    robots_txt_content = Column(Text)
    robots_txt_updated_at = Column(DateTime)
    last_crawl_at = Column(DateTime, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    """Create all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    """Drop all database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
