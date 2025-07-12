"""
Core crawler service implementation.
"""

import asyncio
import hashlib
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, urlparse, urlencode
import re

import httpx
from bs4 import BeautifulSoup
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.config import settings
from app.core.cache import CacheManager
from app.core.database import PageMetadataModel, CrawlQueueModel, CrawlHistoryModel
from app.services.parser import HTMLParser
from app.services.classifier import ContentClassifier
from app.services.rate_limiter import RateLimiter
from app.services.robots_checker import RobotsChecker
from shared.models import (
    CrawlRequest, 
    BatchCrawlRequest, 
    CrawlStatus, 
    PageMetadata,
    Priority,
    ContentType,
    TopicClassification
)

logger = structlog.get_logger()


class CrawlerService:
    """Main crawler service implementation."""
    
    def __init__(self, db: AsyncSession, cache: CacheManager):
        self.db = db
        self.cache = cache
        self.html_parser = HTMLParser()
        self.classifier = ContentClassifier()
        self.rate_limiter = RateLimiter(cache)
        self.robots_checker = RobotsChecker(cache)
        
        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                timeout=settings.REQUEST_TIMEOUT,
                connect=10.0,
                read=settings.REQUEST_TIMEOUT,
            ),
            limits=httpx.Limits(
                max_connections=settings.MAX_CONCURRENT_REQUESTS,
                max_keepalive_connections=20,
            ),
            headers={
                "User-Agent": settings.DEFAULT_USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            },
        )
    
    async def process_crawl_request(self, crawl_id: str, request: CrawlRequest) -> None:
        """Process a single crawl request."""
        try:
            # Update status to processing
            await self._update_crawl_status(crawl_id, CrawlStatus.PROCESSING)
            
            # Check robots.txt if required
            if request.respect_robots_txt:
                can_crawl = await self.robots_checker.can_crawl(
                    str(request.url), 
                    request.user_agent or settings.DEFAULT_USER_AGENT
                )
                if not can_crawl:
                    await self._update_crawl_status(
                        crawl_id, 
                        CrawlStatus.FAILED, 
                        "Blocked by robots.txt"
                    )
                    return
            
            # Check rate limiting
            await self.rate_limiter.wait_for_domain(request.url.host, request.crawl_delay)
            
            # Crawl the URL
            result = await self._crawl_url(str(request.url), request)
            
            if result:
                # Save metadata to database
                await self._save_page_metadata(crawl_id, result)
                await self._update_crawl_status(crawl_id, CrawlStatus.COMPLETED)
                
                # Cache the result
                cache_key = await self.cache.get_crawl_result_key(crawl_id)
                await self.cache.set(cache_key, result.dict(), ttl=3600)
                
                logger.info(
                    "crawl_completed",
                    crawl_id=crawl_id,
                    url=str(request.url),
                    status_code=result.status_code,
                    response_time_ms=result.response_time_ms,
                )
            else:
                await self._update_crawl_status(crawl_id, CrawlStatus.FAILED, "Failed to crawl URL")
                
        except Exception as e:
            logger.error(
                "crawl_failed",
                crawl_id=crawl_id,
                url=str(request.url),
                error=str(e),
                exc_info=True,
            )
            await self._update_crawl_status(crawl_id, CrawlStatus.FAILED, str(e))
    
    async def process_batch_crawl_request(self, batch_id: str, request: BatchCrawlRequest) -> None:
        """Process a batch crawl request."""
        try:
            # Create individual crawl requests
            tasks = []
            for url in request.urls:
                individual_request = CrawlRequest(
                    url=url,
                    priority=request.priority,
                    max_retries=request.max_retries,
                    crawl_delay=request.crawl_delay,
                    respect_robots_txt=request.respect_robots_txt,
                    user_agent=request.user_agent,
                    headers=request.headers,
                )
                
                # Generate crawl ID for this URL
                crawl_id = await self._get_crawl_id_for_url(str(url))
                
                tasks.append(self.process_crawl_request(crawl_id, individual_request))
            
            # Process all URLs concurrently with semaphore to limit concurrency
            semaphore = asyncio.Semaphore(10)  # Limit to 10 concurrent requests
            
            async def process_with_semaphore(task):
                async with semaphore:
                    return await task
            
            await asyncio.gather(*[process_with_semaphore(task) for task in tasks])
            
            logger.info(
                "batch_crawl_completed",
                batch_id=batch_id,
                url_count=len(request.urls),
            )
            
        except Exception as e:
            logger.error(
                "batch_crawl_failed",
                batch_id=batch_id,
                error=str(e),
                exc_info=True,
            )
    
    async def _crawl_url(self, url: str, request: CrawlRequest) -> Optional[PageMetadata]:
        """Crawl a single URL and extract metadata."""
        start_time = time.time()
        
        try:
            # Prepare headers
            headers = dict(request.headers) if request.headers else {}
            if request.user_agent:
                headers["User-Agent"] = request.user_agent
            
            # Make HTTP request
            response = await self.client.get(url, headers=headers)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Check if response is successful
            if response.status_code != 200:
                logger.warning(
                    "crawl_non_200_response",
                    url=url,
                    status_code=response.status_code,
                )
                return None
            
            # Check content type
            content_type = response.headers.get("content-type", "").lower()
            if not content_type.startswith("text/html"):
                logger.warning(
                    "crawl_non_html_content",
                    url=url,
                    content_type=content_type,
                )
                return None
            
            # Check content size
            content_length = len(response.content)
            if content_length > settings.MAX_CONTENT_SIZE:
                logger.warning(
                    "crawl_content_too_large",
                    url=url,
                    content_length=content_length,
                    max_size=settings.MAX_CONTENT_SIZE,
                )
                return None
            
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract metadata
            metadata = await self.html_parser.extract_metadata(soup, url)
            
            # Classify content topics
            if settings.ENABLE_TOPIC_CLASSIFICATION:
                topics = await self.classifier.classify_content(soup, metadata)
                metadata.topics = topics
            
            # Add technical metadata
            metadata.response_time_ms = response_time_ms
            metadata.status_code = response.status_code
            metadata.content_hash = hashlib.sha256(response.content).hexdigest()
            metadata.headers = dict(response.headers)
            metadata.crawl_timestamp = datetime.utcnow()
            
            # Record crawl history
            await self._record_crawl_history(
                url=url,
                domain=urlparse(url).netloc,
                status="completed",
                status_code=response.status_code,
                response_time_ms=response_time_ms,
            )
            
            return metadata
            
        except httpx.TimeoutException:
            logger.error("crawl_timeout", url=url)
            await self._record_crawl_history(
                url=url,
                domain=urlparse(url).netloc,
                status="timeout",
                error_message="Request timeout",
            )
            return None
            
        except httpx.RequestError as e:
            logger.error("crawl_request_error", url=url, error=str(e))
            await self._record_crawl_history(
                url=url,
                domain=urlparse(url).netloc,
                status="error",
                error_message=str(e),
            )
            return None
            
        except Exception as e:
            logger.error("crawl_unexpected_error", url=url, error=str(e), exc_info=True)
            await self._record_crawl_history(
                url=url,
                domain=urlparse(url).netloc,
                status="error",
                error_message=str(e),
            )
            return None
    
    async def _save_page_metadata(self, crawl_id: str, metadata: PageMetadata) -> None:
        """Save page metadata to database."""
        try:
            page_metadata = PageMetadataModel(
                crawl_id=crawl_id,
                url=str(metadata.url),
                domain=metadata.url.host,
                title=metadata.title,
                description=metadata.description,
                keywords=metadata.keywords,
                author=metadata.author,
                published_date=metadata.published_date,
                canonical_url=str(metadata.canonical_url) if metadata.canonical_url else None,
                language=metadata.language,
                content_type=metadata.content_type,
                word_count=metadata.word_count,
                images=[img.dict() for img in metadata.images],
                links=[link.dict() for link in metadata.links],
                topics=[topic.dict() for topic in metadata.topics],
                headers=metadata.headers,
                content_hash=metadata.content_hash,
                response_time_ms=metadata.response_time_ms,
                status_code=metadata.status_code,
                crawl_timestamp=metadata.crawl_timestamp,
            )
            
            self.db.add(page_metadata)
            await self.db.commit()
            
        except Exception as e:
            logger.error(
                "save_metadata_failed",
                crawl_id=crawl_id,
                error=str(e),
                exc_info=True,
            )
            await self.db.rollback()
            raise
    
    async def _update_crawl_status(
        self, 
        crawl_id: str, 
        status: CrawlStatus, 
        error_message: str = None
    ) -> None:
        """Update crawl status in database."""
        try:
            update_data = {
                "status": status.value,
                "updated_at": datetime.utcnow(),
            }
            
            if status == CrawlStatus.PROCESSING:
                update_data["processing_started_at"] = datetime.utcnow()
            elif status in [CrawlStatus.COMPLETED, CrawlStatus.FAILED]:
                update_data["completed_at"] = datetime.utcnow()
            
            if error_message:
                update_data["error_message"] = error_message
            
            query = (
                update(CrawlQueueModel)
                .where(CrawlQueueModel.crawl_id == crawl_id)
                .values(**update_data)
            )
            
            await self.db.execute(query)
            await self.db.commit()
            
        except Exception as e:
            logger.error(
                "update_crawl_status_failed",
                crawl_id=crawl_id,
                status=status,
                error=str(e),
                exc_info=True,
            )
            await self.db.rollback()
    
    async def _record_crawl_history(
        self, 
        url: str, 
        domain: str, 
        status: str, 
        status_code: int = None,
        response_time_ms: int = None,
        error_message: str = None,
    ) -> None:
        """Record crawl history for analytics."""
        try:
            history_entry = CrawlHistoryModel(
                crawl_id=None,  # Will be set when we have the crawl_id
                url=url,
                domain=domain,
                status=status,
                status_code=status_code,
                response_time_ms=response_time_ms,
                error_message=error_message,
                crawl_timestamp=datetime.utcnow(),
            )
            
            self.db.add(history_entry)
            await self.db.commit()
            
        except Exception as e:
            logger.error(
                "record_crawl_history_failed",
                url=url,
                error=str(e),
                exc_info=True,
            )
            await self.db.rollback()
    
    async def _get_crawl_id_for_url(self, url: str) -> str:
        """Get crawl ID for a URL from the database."""
        try:
            query = select(CrawlQueueModel.crawl_id).where(CrawlQueueModel.url == url)
            result = await self.db.execute(query)
            crawl_id = result.scalar_one_or_none()
            return str(crawl_id) if crawl_id else None
            
        except Exception as e:
            logger.error(
                "get_crawl_id_failed",
                url=url,
                error=str(e),
                exc_info=True,
            )
            return None
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
