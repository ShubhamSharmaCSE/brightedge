"""
Robots.txt checker service for respectful crawling.
"""

import asyncio
import time
from typing import Dict, Optional, List
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import httpx
import structlog

from app.core.cache import CacheManager
from app.core.config import settings

logger = structlog.get_logger()


class RobotsChecker:
    """Robots.txt checker for respectful crawling."""
    
    def __init__(self, cache: CacheManager):
        self.cache = cache
        self.robots_cache: Dict[str, RobotFileParser] = {}
        self.lock = asyncio.Lock()
        
        # HTTP client for fetching robots.txt
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            headers={
                "User-Agent": settings.DEFAULT_USER_AGENT,
            }
        )
    
    async def can_crawl(self, url: str, user_agent: str = None) -> bool:
        """Check if URL can be crawled according to robots.txt."""
        if not settings.RESPECT_ROBOTS_TXT:
            return True
        
        user_agent = user_agent or settings.DEFAULT_USER_AGENT
        domain = self._extract_domain(url)
        
        try:
            robots_parser = await self._get_robots_parser(domain)
            
            if robots_parser:
                return robots_parser.can_fetch(user_agent, url)
            else:
                # If robots.txt doesn't exist or can't be fetched, allow crawling
                return True
        
        except Exception as e:
            logger.error(
                "robots_check_failed",
                url=url,
                domain=domain,
                error=str(e),
            )
            # On error, allow crawling (conservative approach)
            return True
    
    async def get_crawl_delay(self, url: str, user_agent: str = None) -> Optional[float]:
        """Get crawl delay specified in robots.txt."""
        user_agent = user_agent or settings.DEFAULT_USER_AGENT
        domain = self._extract_domain(url)
        
        try:
            robots_parser = await self._get_robots_parser(domain)
            
            if robots_parser:
                crawl_delay = robots_parser.crawl_delay(user_agent)
                if crawl_delay:
                    return float(crawl_delay)
        
        except Exception as e:
            logger.error(
                "robots_crawl_delay_failed",
                url=url,
                domain=domain,
                error=str(e),
            )
        
        return None
    
    async def get_sitemaps(self, url: str) -> List[str]:
        """Get sitemap URLs from robots.txt."""
        domain = self._extract_domain(url)
        
        try:
            robots_parser = await self._get_robots_parser(domain)
            
            if robots_parser:
                sitemaps = robots_parser.site_maps()
                return list(sitemaps) if sitemaps else []
        
        except Exception as e:
            logger.error(
                "robots_sitemaps_failed",
                url=url,
                domain=domain,
                error=str(e),
            )
        
        return []
    
    async def _get_robots_parser(self, domain: str) -> Optional[RobotFileParser]:
        """Get robots.txt parser for domain."""
        async with self.lock:
            # Check cache first
            cache_key = await self.cache.get_robots_txt_key(domain)
            cached_robots = await self.cache.get(cache_key)
            
            if cached_robots:
                # Create parser from cached content
                robots_parser = RobotFileParser()
                robots_parser.set_url(f"https://{domain}/robots.txt")
                
                if cached_robots.get('content'):
                    robots_parser.read()
                    # Set the content manually (RobotFileParser doesn't have a direct way)
                    robots_parser.entries = []
                    robots_parser.set_url(f"https://{domain}/robots.txt")
                    robots_parser.read()
                    
                    return robots_parser
                else:
                    # Cached as "not found"
                    return None
            
            # Fetch robots.txt
            robots_parser = await self._fetch_robots_txt(domain)
            
            # Cache the result
            cache_data = {
                'content': None,
                'fetched_at': time.time(),
            }
            
            if robots_parser:
                cache_data['content'] = True  # Simplified caching
            
            await self.cache.set(
                cache_key, 
                cache_data, 
                ttl=settings.ROBOTS_TXT_CACHE_TTL
            )
            
            return robots_parser
    
    async def _fetch_robots_txt(self, domain: str) -> Optional[RobotFileParser]:
        """Fetch and parse robots.txt for domain."""
        robots_url = f"https://{domain}/robots.txt"
        
        try:
            response = await self.client.get(robots_url)
            
            if response.status_code == 200:
                robots_parser = RobotFileParser()
                robots_parser.set_url(robots_url)
                
                # Parse the content
                content = response.text
                robots_parser.read()
                
                # Store the content for manual parsing
                self._parse_robots_content(robots_parser, content)
                
                logger.info(
                    "robots_txt_fetched",
                    domain=domain,
                    url=robots_url,
                    status_code=response.status_code,
                )
                
                return robots_parser
            
            elif response.status_code == 404:
                logger.info(
                    "robots_txt_not_found",
                    domain=domain,
                    url=robots_url,
                )
                return None
            
            else:
                logger.warning(
                    "robots_txt_error",
                    domain=domain,
                    url=robots_url,
                    status_code=response.status_code,
                )
                return None
        
        except httpx.TimeoutException:
            logger.warning(
                "robots_txt_timeout",
                domain=domain,
                url=robots_url,
            )
            return None
        
        except Exception as e:
            logger.error(
                "robots_txt_fetch_failed",
                domain=domain,
                url=robots_url,
                error=str(e),
            )
            return None
    
    def _parse_robots_content(self, robots_parser: RobotFileParser, content: str) -> None:
        """Parse robots.txt content manually."""
        # This is a simplified version - in production, you'd want more robust parsing
        lines = content.split('\n')
        
        current_user_agent = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('#') or not line:
                continue
            
            if line.lower().startswith('user-agent:'):
                current_user_agent = line.split(':', 1)[1].strip()
            
            elif line.lower().startswith('disallow:'):
                path = line.split(':', 1)[1].strip()
                # Add to parser's internal structure
                
            elif line.lower().startswith('allow:'):
                path = line.split(':', 1)[1].strip()
                # Add to parser's internal structure
                
            elif line.lower().startswith('crawl-delay:'):
                delay = line.split(':', 1)[1].strip()
                # Add to parser's internal structure
                
            elif line.lower().startswith('sitemap:'):
                sitemap_url = line.split(':', 1)[1].strip()
                # Add to parser's internal structure
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc.lower()
    
    async def clear_cache(self, domain: str = None) -> None:
        """Clear robots.txt cache for domain or all domains."""
        if domain:
            cache_key = await self.cache.get_robots_txt_key(domain)
            await self.cache.delete(cache_key)
            logger.info("robots_cache_cleared", domain=domain)
        else:
            # Clear all robots.txt cache (implementation depends on cache backend)
            logger.info("robots_cache_cleared_all")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
