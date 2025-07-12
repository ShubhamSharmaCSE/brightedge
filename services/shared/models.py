"""
Shared data models and schemas for the crawler services.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, validator
from enum import Enum


class CrawlStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


class ContentType(str, Enum):
    HTML = "text/html"
    PDF = "application/pdf"
    IMAGE = "image"
    OTHER = "other"


class Priority(int, Enum):
    LOW = 1
    NORMAL = 5
    HIGH = 10


class ImageMetadata(BaseModel):
    """Metadata for images found on the page."""
    url: HttpUrl
    alt_text: Optional[str] = None
    title: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class LinkMetadata(BaseModel):
    """Metadata for links found on the page."""
    url: HttpUrl
    text: Optional[str] = None
    title: Optional[str] = None
    rel: Optional[str] = None


class TopicClassification(BaseModel):
    """Topic classification result."""
    topic: str
    confidence: float = Field(ge=0.0, le=1.0)
    keywords: List[str] = Field(default_factory=list)


class PageMetadata(BaseModel):
    """Complete metadata extracted from a web page."""
    url: HttpUrl
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    author: Optional[str] = None
    published_date: Optional[datetime] = None
    canonical_url: Optional[HttpUrl] = None
    language: Optional[str] = None
    content_type: ContentType = ContentType.HTML
    word_count: int = 0
    images: List[ImageMetadata] = Field(default_factory=list)
    links: List[LinkMetadata] = Field(default_factory=list)
    topics: List[TopicClassification] = Field(default_factory=list)
    crawl_timestamp: datetime = Field(default_factory=datetime.utcnow)
    response_time_ms: int = 0
    status_code: int = 200
    content_hash: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    
    @validator('keywords', pre=True)
    def parse_keywords(cls, v):
        if isinstance(v, str):
            return [k.strip() for k in v.split(',') if k.strip()]
        return v or []


class CrawlRequest(BaseModel):
    """Request to crawl a single URL."""
    url: HttpUrl
    priority: Priority = Priority.NORMAL
    max_retries: int = Field(default=3, ge=0, le=10)
    crawl_delay: float = Field(default=1.0, ge=0.1, le=60.0)
    respect_robots_txt: bool = True
    user_agent: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    
    class Config:
        schema_extra = {
            "example": {
                "url": "https://www.example.com",
                "priority": 5,
                "max_retries": 3,
                "crawl_delay": 1.0,
                "respect_robots_txt": True
            }
        }


class BatchCrawlRequest(BaseModel):
    """Request to crawl multiple URLs."""
    urls: List[HttpUrl] = Field(min_items=1, max_items=1000)
    priority: Priority = Priority.NORMAL
    max_retries: int = Field(default=3, ge=0, le=10)
    crawl_delay: float = Field(default=1.0, ge=0.1, le=60.0)
    respect_robots_txt: bool = True
    user_agent: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    
    class Config:
        schema_extra = {
            "example": {
                "urls": [
                    "https://www.example.com",
                    "https://www.google.com"
                ],
                "priority": 5,
                "max_retries": 3,
                "crawl_delay": 1.0,
                "respect_robots_txt": True
            }
        }


class CrawlResult(BaseModel):
    """Result of a crawl operation."""
    crawl_id: str
    url: HttpUrl
    status: CrawlStatus
    metadata: Optional[PageMetadata] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    class Config:
        schema_extra = {
            "example": {
                "crawl_id": "123e4567-e89b-12d3-a456-426614174000",
                "url": "https://www.example.com",
                "status": "completed",
                "metadata": {
                    "title": "Example Domain",
                    "description": "This domain is for use in illustrative examples",
                    "word_count": 100,
                    "topics": [
                        {
                            "topic": "technology",
                            "confidence": 0.85,
                            "keywords": ["example", "domain", "web"]
                        }
                    ]
                }
            }
        }


class BatchCrawlResult(BaseModel):
    """Result of a batch crawl operation."""
    batch_id: str
    total_urls: int
    completed_urls: int
    failed_urls: int
    results: List[CrawlResult]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_urls == 0:
            return 0.0
        return self.completed_urls / self.total_urls


class HealthCheck(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str
    database: bool = False
    redis: bool = False
    queue: bool = False
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-01T12:00:00Z",
                "version": "1.0.0",
                "database": True,
                "redis": True,
                "queue": True
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid URL format",
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req-123"
            }
        }
