"""Cache manager supporting Redis and in-memory caching."""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Any, Dict
from loguru import logger

from config import settings


class CacheManager:
    """
    Hybrid cache manager with Redis and in-memory fallback.
    """
    
    def __init__(self):
        self._memory_cache: Dict[str, tuple[Any, datetime]] = {}
        self._redis = None
        self._redis_available = False
    
    async def initialize(self):
        """Initialize Redis connection if available."""
        if settings.redis_url:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(settings.redis_url)
                await self._redis.ping()
                self._redis_available = True
                logger.info("Redis cache initialized")
            except Exception as e:
                logger.warning(f"Redis not available, using memory cache: {e}")
                self._redis_available = False
    
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        # Try Redis first
        if self._redis_available:
            try:
                value = await self._redis.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"Redis get error: {e}")
        
        # Fallback to memory cache
        if key in self._memory_cache:
            value, expiry = self._memory_cache[key]
            if datetime.now() < expiry:
                return value
            else:
                del self._memory_cache[key]
        
        return None
    
    async def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """Set value in cache with TTL."""
        # Serialize value
        try:
            serialized = json.dumps(value, default=str)
        except (TypeError, ValueError) as e:
            logger.warning(f"Could not serialize value for cache: {e}")
            return
        
        # Try Redis first
        if self._redis_available:
            try:
                await self._redis.setex(key, ttl_seconds, serialized)
            except Exception as e:
                logger.warning(f"Redis set error: {e}")
        
        # Also store in memory cache
        expiry = datetime.now() + timedelta(seconds=ttl_seconds)
        self._memory_cache[key] = (value, expiry)
        
        # Clean up old memory entries periodically
        if len(self._memory_cache) > 1000:
            self._cleanup_memory_cache()
    
    async def delete(self, key: str):
        """Delete value from cache."""
        if self._redis_available:
            try:
                await self._redis.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")
        
        if key in self._memory_cache:
            del self._memory_cache[key]
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if self._redis_available:
            try:
                return await self._redis.exists(key)
            except Exception:
                pass
        
        if key in self._memory_cache:
            _, expiry = self._memory_cache[key]
            return datetime.now() < expiry
        
        return False
    
    def _cleanup_memory_cache(self):
        """Remove expired entries from memory cache."""
        now = datetime.now()
        expired_keys = [
            key for key, (_, expiry) in self._memory_cache.items()
            if now >= expiry
        ]
        for key in expired_keys:
            del self._memory_cache[key]
    
    # Convenience methods for specific data types
    
    async def get_price(self, ticker: str) -> Optional[dict]:
        """Get cached price data."""
        return await self.get(f"price:{ticker}")
    
    async def set_price(self, ticker: str, data: dict):
        """Cache price data."""
        await self.set(f"price:{ticker}", data, settings.price_cache_ttl)
    
    async def get_stock_data(self, ticker: str) -> Optional[dict]:
        """Get cached stock data."""
        return await self.get(f"stock:{ticker}")
    
    async def set_stock_data(self, ticker: str, data: dict):
        """Cache stock data."""
        await self.set(f"stock:{ticker}", data, settings.fundamental_cache_ttl)
    
    async def get_news(self, ticker: str) -> Optional[dict]:
        """Get cached news data."""
        return await self.get(f"news:{ticker}")
    
    async def set_news(self, ticker: str, data: dict):
        """Cache news data."""
        await self.set(f"news:{ticker}", data, settings.news_cache_ttl)
    
    async def get_analysis(self, ticker: str, analysis_type: str) -> Optional[dict]:
        """Get cached analysis result."""
        return await self.get(f"analysis:{analysis_type}:{ticker}")
    
    async def set_analysis(self, ticker: str, analysis_type: str, data: dict, ttl: int = 1800):
        """Cache analysis result (default 30 min)."""
        await self.set(f"analysis:{analysis_type}:{ticker}", data, ttl)


# Global cache instance
cache = CacheManager()
