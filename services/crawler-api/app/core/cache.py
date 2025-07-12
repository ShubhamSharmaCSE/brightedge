"""
Cache management using Redis.
"""

import json
import redis.asyncio as redis
from typing import Optional, Any, Dict
from app.core.config import get_redis_url, settings
import structlog

logger = structlog.get_logger()


class CacheManager:
    """Redis cache manager."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis_client = redis.from_url(
                get_redis_url(),
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            # Test connection
            await self.redis_client.ping()
            logger.info("redis_connected")
        except Exception as e:
            logger.error("redis_connection_failed", error=str(e))
            raise
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("redis_disconnected")
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error("cache_get_failed", key=key, error=str(e))
            return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache."""
        if not self.redis_client:
            return False
        
        try:
            serialized_value = json.dumps(value, default=str)
            ttl = ttl or settings.REDIS_CACHE_TTL
            await self.redis_client.setex(key, ttl, serialized_value)
            return True
        except Exception as e:
            logger.error("cache_set_failed", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error("cache_delete_failed", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.redis_client:
            return False
        
        try:
            return await self.redis_client.exists(key)
        except Exception as e:
            logger.error("cache_exists_failed", key=key, error=str(e))
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter in cache."""
        if not self.redis_client:
            return None
        
        try:
            return await self.redis_client.incrby(key, amount)
        except Exception as e:
            logger.error("cache_increment_failed", key=key, error=str(e))
            return None
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time for key."""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.expire(key, seconds)
            return True
        except Exception as e:
            logger.error("cache_expire_failed", key=key, error=str(e))
            return False
    
    async def get_rate_limit_key(self, domain: str) -> str:
        """Get rate limit key for domain."""
        return f"rate_limit:{domain}"
    
    async def get_robots_txt_key(self, domain: str) -> str:
        """Get robots.txt cache key for domain."""
        return f"robots_txt:{domain}"
    
    async def get_crawl_result_key(self, crawl_id: str) -> str:
        """Get crawl result cache key."""
        return f"crawl_result:{crawl_id}"


# Global cache manager instance
cache_manager = CacheManager()


async def get_cache() -> CacheManager:
    """Get cache manager instance."""
    if not cache_manager.redis_client:
        await cache_manager.connect()
    return cache_manager
