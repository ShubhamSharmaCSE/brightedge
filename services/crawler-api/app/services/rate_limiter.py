"""
Rate limiting service for domain-aware crawling.
"""

import asyncio
import time
from typing import Dict, Optional
from urllib.parse import urlparse
import structlog

from app.core.cache import CacheManager
from app.core.config import settings

logger = structlog.get_logger()


class RateLimiter:
    """Domain-aware rate limiter for respectful crawling."""
    
    def __init__(self, cache: CacheManager):
        self.cache = cache
        self.last_request_times: Dict[str, float] = {}
        self.request_counts: Dict[str, int] = {}
        self.lock = asyncio.Lock()
    
    async def wait_for_domain(self, domain: str, crawl_delay: float = None) -> None:
        """Wait for rate limit before crawling a domain."""
        async with self.lock:
            crawl_delay = crawl_delay or settings.DEFAULT_CRAWL_DELAY
            
            # Get rate limit info from cache
            rate_limit_key = await self.cache.get_rate_limit_key(domain)
            rate_limit_info = await self.cache.get(rate_limit_key)
            
            if rate_limit_info:
                last_request_time = rate_limit_info.get('last_request_time', 0)
                request_count = rate_limit_info.get('request_count', 0)
                domain_crawl_delay = rate_limit_info.get('crawl_delay', crawl_delay)
            else:
                last_request_time = 0
                request_count = 0
                domain_crawl_delay = crawl_delay
            
            current_time = time.time()
            time_since_last_request = current_time - last_request_time
            
            # Check if we need to wait
            if time_since_last_request < domain_crawl_delay:
                wait_time = domain_crawl_delay - time_since_last_request
                logger.info(
                    "rate_limit_wait",
                    domain=domain,
                    wait_time=wait_time,
                    crawl_delay=domain_crawl_delay,
                )
                await asyncio.sleep(wait_time)
                current_time = time.time()
            
            # Update rate limit info
            new_request_count = request_count + 1
            rate_limit_info = {
                'last_request_time': current_time,
                'request_count': new_request_count,
                'crawl_delay': domain_crawl_delay,
            }
            
            await self.cache.set(rate_limit_key, rate_limit_info, ttl=3600)
            
            logger.debug(
                "rate_limit_updated",
                domain=domain,
                request_count=new_request_count,
                crawl_delay=domain_crawl_delay,
            )
    
    async def get_domain_stats(self, domain: str) -> Dict[str, any]:
        """Get crawling statistics for a domain."""
        rate_limit_key = await self.cache.get_rate_limit_key(domain)
        rate_limit_info = await self.cache.get(rate_limit_key)
        
        if not rate_limit_info:
            return {
                'request_count': 0,
                'last_request_time': None,
                'crawl_delay': settings.DEFAULT_CRAWL_DELAY,
            }
        
        return {
            'request_count': rate_limit_info.get('request_count', 0),
            'last_request_time': rate_limit_info.get('last_request_time'),
            'crawl_delay': rate_limit_info.get('crawl_delay', settings.DEFAULT_CRAWL_DELAY),
        }
    
    async def set_domain_crawl_delay(self, domain: str, crawl_delay: float) -> None:
        """Set custom crawl delay for a domain."""
        rate_limit_key = await self.cache.get_rate_limit_key(domain)
        rate_limit_info = await self.cache.get(rate_limit_key) or {}
        
        rate_limit_info['crawl_delay'] = crawl_delay
        await self.cache.set(rate_limit_key, rate_limit_info, ttl=3600)
        
        logger.info(
            "domain_crawl_delay_updated",
            domain=domain,
            crawl_delay=crawl_delay,
        )
    
    async def is_rate_limited(self, domain: str) -> bool:
        """Check if domain is currently rate limited."""
        rate_limit_key = await self.cache.get_rate_limit_key(domain)
        rate_limit_info = await self.cache.get(rate_limit_key)
        
        if not rate_limit_info:
            return False
        
        last_request_time = rate_limit_info.get('last_request_time', 0)
        crawl_delay = rate_limit_info.get('crawl_delay', settings.DEFAULT_CRAWL_DELAY)
        
        current_time = time.time()
        time_since_last_request = current_time - last_request_time
        
        return time_since_last_request < crawl_delay
    
    async def reset_domain_stats(self, domain: str) -> None:
        """Reset statistics for a domain."""
        rate_limit_key = await self.cache.get_rate_limit_key(domain)
        await self.cache.delete(rate_limit_key)
        
        logger.info("domain_stats_reset", domain=domain)
    
    async def get_all_domain_stats(self) -> Dict[str, Dict[str, any]]:
        """Get statistics for all domains (for monitoring)."""
        # This would require Redis SCAN or similar to find all rate limit keys
        # For now, return empty dict - in production, you'd implement this
        return {}
    
    def extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc.lower()
    
    async def cleanup_old_stats(self, max_age_hours: int = 24) -> int:
        """Clean up old rate limiting statistics."""
        # This would clean up old entries from cache
        # Implementation depends on your cache backend
        # For Redis, you could use TTL or manual cleanup
        return 0
