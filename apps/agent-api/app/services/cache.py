"""
Redis caching service for improved performance
"""
import json
import hashlib
from typing import Any, Optional, Callable
from functools import wraps

import redis
from redis.exceptions import RedisError

from app.config.settings import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Global Redis client
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """Get or create Redis client"""
    global _redis_client

    if not settings.redis_enabled:
        return None

    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            _redis_client.ping()
            logger.info("Redis client initialized successfully")
        except RedisError as e:
            logger.warning(f"Failed to connect to Redis: {e}. Caching disabled.")
            _redis_client = None

    return _redis_client


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from function arguments"""
    # Create a stable string representation of arguments
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_string = ":".join(key_parts)

    # Hash for consistent length
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(
    ttl: Optional[int] = None,
    key_prefix: str = "",
    enabled: bool = True,
):
    """
    Decorator to cache function results in Redis

    Args:
        ttl: Time to live in seconds (default: settings.cache_ttl_seconds)
        key_prefix: Prefix for cache key
        enabled: Whether caching is enabled
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            if not enabled or not settings.redis_enabled:
                return await func(*args, **kwargs)

            client = get_redis_client()
            if client is None:
                return await func(*args, **kwargs)

            # Generate cache key
            func_key = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"

            try:
                # Try to get from cache
                cached_value = client.get(func_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit for {func_key}")
                    return json.loads(cached_value)

                # Cache miss - execute function
                logger.debug(f"Cache miss for {func_key}")
                result = await func(*args, **kwargs)

                # Store in cache
                cache_ttl = ttl or settings.cache_ttl_seconds
                client.setex(
                    func_key,
                    cache_ttl,
                    json.dumps(result, default=str)
                )

                return result

            except (RedisError, json.JSONDecodeError) as e:
                logger.warning(f"Cache error: {e}. Falling back to direct execution.")
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            if not enabled or not settings.redis_enabled:
                return func(*args, **kwargs)

            client = get_redis_client()
            if client is None:
                return func(*args, **kwargs)

            # Generate cache key
            func_key = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"

            try:
                # Try to get from cache
                cached_value = client.get(func_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit for {func_key}")
                    return json.loads(cached_value)

                # Cache miss - execute function
                logger.debug(f"Cache miss for {func_key}")
                result = func(*args, **kwargs)

                # Store in cache
                cache_ttl = ttl or settings.cache_ttl_seconds
                client.setex(
                    func_key,
                    cache_ttl,
                    json.dumps(result, default=str)
                )

                return result

            except (RedisError, json.JSONDecodeError) as e:
                logger.warning(f"Cache error: {e}. Falling back to direct execution.")
                return func(*args, **kwargs)

        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def invalidate_cache(key_pattern: str) -> int:
    """
    Invalidate cache entries matching a pattern

    Args:
        key_pattern: Redis key pattern (e.g., "leads:*")

    Returns:
        Number of keys deleted
    """
    if not settings.redis_enabled:
        return 0

    client = get_redis_client()
    if client is None:
        return 0

    try:
        keys = client.keys(key_pattern)
        if keys:
            deleted = client.delete(*keys)
            logger.info(f"Invalidated {deleted} cache entries matching {key_pattern}")
            return deleted
        return 0
    except RedisError as e:
        logger.warning(f"Failed to invalidate cache: {e}")
        return 0


def get_cache_stats() -> dict:
    """Get cache statistics"""
    if not settings.redis_enabled:
        return {"enabled": False}

    client = get_redis_client()
    if client is None:
        return {"enabled": False, "connected": False}

    try:
        info = client.info("stats")
        return {
            "enabled": True,
            "connected": True,
            "total_commands_processed": info.get("total_commands_processed", 0),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "hit_rate": info.get("keyspace_hits", 0) / max(
                info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1
            ),
        }
    except RedisError as e:
        logger.warning(f"Failed to get cache stats: {e}")
        return {"enabled": True, "connected": False, "error": str(e)}
