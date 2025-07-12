"""
Main crawler API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
import uuid
import structlog

from app.core.database import get_db, PageMetadataModel, CrawlQueueModel
from app.core.cache import get_cache, CacheManager
from app.services.crawler import CrawlerService
from shared.models import (
    CrawlRequest, 
    BatchCrawlRequest, 
    CrawlResult, 
    BatchCrawlResult,
    CrawlStatus,
    PageMetadata
)

logger = structlog.get_logger()
router = APIRouter()


@router.post("/crawl", response_model=CrawlResult)
async def crawl_url(
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    cache: CacheManager = Depends(get_cache),
):
    """
    Crawl a single URL and extract metadata.
    
    This endpoint accepts a URL and crawls it to extract metadata including:
    - Title, description, keywords
    - Content classification and topics
    - Links and images
    - Technical metadata (response time, status code, etc.)
    
    The crawling is performed asynchronously in the background.
    """
    
    # Generate crawl ID
    crawl_id = str(uuid.uuid4())
    
    # Create crawl queue entry
    crawl_queue_entry = CrawlQueueModel(
        crawl_id=crawl_id,
        url=str(request.url),
        domain=request.url.host,
        priority=request.priority,
        max_retries=request.max_retries,
        crawl_delay=request.crawl_delay,
        respect_robots_txt=request.respect_robots_txt,
        user_agent=request.user_agent,
        headers=request.headers,
        status=CrawlStatus.PENDING,
    )
    
    db.add(crawl_queue_entry)
    await db.commit()
    
    # Start crawling in background
    crawler_service = CrawlerService(db, cache)
    background_tasks.add_task(
        crawler_service.process_crawl_request,
        crawl_id,
        request
    )
    
    logger.info(
        "crawl_request_queued",
        crawl_id=crawl_id,
        url=str(request.url),
        domain=request.url.host,
    )
    
    return CrawlResult(
        crawl_id=crawl_id,
        url=request.url,
        status=CrawlStatus.PENDING,
    )


@router.post("/crawl/batch", response_model=BatchCrawlResult)
async def crawl_urls_batch(
    request: BatchCrawlRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    cache: CacheManager = Depends(get_cache),
):
    """
    Crawl multiple URLs in batch.
    
    This endpoint accepts a list of URLs and crawls them asynchronously.
    Each URL is processed independently and the results are returned
    when all URLs have been processed.
    """
    
    # Generate batch ID
    batch_id = str(uuid.uuid4())
    crawl_results = []
    
    # Create crawl queue entries for all URLs
    for url in request.urls:
        crawl_id = str(uuid.uuid4())
        
        crawl_queue_entry = CrawlQueueModel(
            crawl_id=crawl_id,
            url=str(url),
            domain=url.host,
            priority=request.priority,
            max_retries=request.max_retries,
            crawl_delay=request.crawl_delay,
            respect_robots_txt=request.respect_robots_txt,
            user_agent=request.user_agent,
            headers=request.headers,
            status=CrawlStatus.PENDING,
        )
        
        db.add(crawl_queue_entry)
        
        crawl_results.append(CrawlResult(
            crawl_id=crawl_id,
            url=url,
            status=CrawlStatus.PENDING,
        ))
    
    await db.commit()
    
    # Start batch crawling in background
    crawler_service = CrawlerService(db, cache)
    background_tasks.add_task(
        crawler_service.process_batch_crawl_request,
        batch_id,
        request
    )
    
    logger.info(
        "batch_crawl_request_queued",
        batch_id=batch_id,
        url_count=len(request.urls),
    )
    
    return BatchCrawlResult(
        batch_id=batch_id,
        total_urls=len(request.urls),
        completed_urls=0,
        failed_urls=0,
        results=crawl_results,
    )


@router.get("/results/{crawl_id}", response_model=CrawlResult)
async def get_crawl_result(
    crawl_id: str,
    db: AsyncSession = Depends(get_db),
    cache: CacheManager = Depends(get_cache),
):
    """
    Get the result of a crawl operation.
    
    Returns the metadata and status of a crawl operation by its ID.
    """
    
    # Try to get from cache first
    cache_key = await cache.get_crawl_result_key(crawl_id)
    cached_result = await cache.get(cache_key)
    
    if cached_result:
        return CrawlResult(**cached_result)
    
    # Query database
    query = select(PageMetadataModel).where(PageMetadataModel.crawl_id == crawl_id)
    result = await db.execute(query)
    page_metadata = result.scalar_one_or_none()
    
    if not page_metadata:
        # Check if it's still in queue
        queue_query = select(CrawlQueueModel).where(CrawlQueueModel.crawl_id == crawl_id)
        queue_result = await db.execute(queue_query)
        queue_entry = queue_result.scalar_one_or_none()
        
        if not queue_entry:
            raise HTTPException(status_code=404, detail="Crawl result not found")
        
        return CrawlResult(
            crawl_id=crawl_id,
            url=queue_entry.url,
            status=CrawlStatus(queue_entry.status),
            error_message=queue_entry.error_message,
            retry_count=queue_entry.retry_count,
            created_at=queue_entry.created_at,
            completed_at=queue_entry.completed_at,
        )
    
    # Convert database model to response model
    metadata = PageMetadata(
        url=page_metadata.url,
        title=page_metadata.title,
        description=page_metadata.description,
        keywords=page_metadata.keywords or [],
        author=page_metadata.author,
        published_date=page_metadata.published_date,
        canonical_url=page_metadata.canonical_url,
        language=page_metadata.language,
        content_type=page_metadata.content_type,
        word_count=page_metadata.word_count,
        images=page_metadata.images or [],
        links=page_metadata.links or [],
        topics=page_metadata.topics or [],
        crawl_timestamp=page_metadata.crawl_timestamp,
        response_time_ms=page_metadata.response_time_ms,
        status_code=page_metadata.status_code,
        content_hash=page_metadata.content_hash,
        headers=page_metadata.headers or {},
    )
    
    crawl_result = CrawlResult(
        crawl_id=crawl_id,
        url=page_metadata.url,
        status=CrawlStatus.COMPLETED,
        metadata=metadata,
        created_at=page_metadata.created_at,
        completed_at=page_metadata.updated_at,
    )
    
    # Cache the result
    await cache.set(cache_key, crawl_result.dict(), ttl=3600)
    
    return crawl_result


@router.get("/results", response_model=List[CrawlResult])
async def get_crawl_results(
    limit: int = 10,
    offset: int = 0,
    domain: str = None,
    status: CrawlStatus = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a list of crawl results with optional filtering.
    
    Returns a paginated list of crawl results with optional filtering by domain and status.
    """
    
    # Build query
    query = select(PageMetadataModel)
    
    if domain:
        query = query.where(PageMetadataModel.domain == domain)
    
    # Add pagination
    query = query.offset(offset).limit(limit)
    query = query.order_by(PageMetadataModel.created_at.desc())
    
    # Execute query
    result = await db.execute(query)
    page_metadata_list = result.scalars().all()
    
    # Convert to response models
    crawl_results = []
    for page_metadata in page_metadata_list:
        metadata = PageMetadata(
            url=page_metadata.url,
            title=page_metadata.title,
            description=page_metadata.description,
            keywords=page_metadata.keywords or [],
            author=page_metadata.author,
            published_date=page_metadata.published_date,
            canonical_url=page_metadata.canonical_url,
            language=page_metadata.language,
            content_type=page_metadata.content_type,
            word_count=page_metadata.word_count,
            images=page_metadata.images or [],
            links=page_metadata.links or [],
            topics=page_metadata.topics or [],
            crawl_timestamp=page_metadata.crawl_timestamp,
            response_time_ms=page_metadata.response_time_ms,
            status_code=page_metadata.status_code,
            content_hash=page_metadata.content_hash,
            headers=page_metadata.headers or {},
        )
        
        crawl_results.append(CrawlResult(
            crawl_id=str(page_metadata.crawl_id),
            url=page_metadata.url,
            status=CrawlStatus.COMPLETED,
            metadata=metadata,
            created_at=page_metadata.created_at,
            completed_at=page_metadata.updated_at,
        ))
    
    return crawl_results


@router.delete("/results/{crawl_id}")
async def delete_crawl_result(
    crawl_id: str,
    db: AsyncSession = Depends(get_db),
    cache: CacheManager = Depends(get_cache),
):
    """
    Delete a crawl result.
    
    Removes a crawl result from the database and cache.
    """
    
    # Delete from database
    query = select(PageMetadataModel).where(PageMetadataModel.crawl_id == crawl_id)
    result = await db.execute(query)
    page_metadata = result.scalar_one_or_none()
    
    if not page_metadata:
        raise HTTPException(status_code=404, detail="Crawl result not found")
    
    await db.delete(page_metadata)
    await db.commit()
    
    # Delete from cache
    cache_key = await cache.get_crawl_result_key(crawl_id)
    await cache.delete(cache_key)
    
    logger.info("crawl_result_deleted", crawl_id=crawl_id)
    
    return {"message": "Crawl result deleted successfully"}
