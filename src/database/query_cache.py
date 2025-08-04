"""Query result caching for improved performance."""

import logging
from functools import lru_cache, wraps
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
import hashlib
import json

logger = logging.getLogger(__name__)


class QueryCache:
    """Simple in-memory query result cache with TTL support."""
    
    def __init__(self, default_ttl: timedelta = timedelta(minutes=5)):
        """Initialize query cache.
        
        Args:
            default_ttl: Default time-to-live for cached entries
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key in self._cache:
            entry = self._cache[key]
            if datetime.utcnow() < entry['expires_at']:
                self.hits += 1
                logger.debug(f"Cache hit for key: {key}")
                return entry['value']
            else:
                # Expired, remove it
                del self._cache[key]
        
        self.misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None):
        """Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live (uses default if not specified)
        """
        ttl = ttl or self.default_ttl
        self._cache[key] = {
            'value': value,
            'expires_at': datetime.utcnow() + ttl,
            'cached_at': datetime.utcnow()
        }
        logger.debug(f"Cached value for key: {key} (TTL: {ttl})")
    
    def invalidate(self, pattern: Optional[str] = None):
        """Invalidate cache entries.
        
        Args:
            pattern: If provided, invalidate only keys containing this pattern
        """
        if pattern:
            keys_to_remove = [k for k in self._cache if pattern in k]
            for key in keys_to_remove:
                del self._cache[key]
            logger.info(f"Invalidated {len(keys_to_remove)} cache entries matching pattern: {pattern}")
        else:
            self._cache.clear()
            logger.info("Invalidated all cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'size': len(self._cache),
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'total_requests': total_requests
        }


class CacheMixin:
    """Mixin to add caching capabilities to database manager."""
    
    def __init__(self, *args, **kwargs):
        """Initialize cache mixin."""
        super().__init__(*args, **kwargs)
        self._query_cache = QueryCache(default_ttl=timedelta(minutes=5))
        self._stats_cache_ttl = timedelta(minutes=5)
        self._dataset_stats_cache_ttl = timedelta(minutes=10)
    
    def _make_cache_key(self, method_name: str, *args, **kwargs) -> str:
        """Generate cache key from method name and arguments.
        
        Args:
            method_name: Name of the method
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Cache key string
        """
        # Create a unique key from method name and arguments
        key_parts = [method_name]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        
        key_string = ":".join(key_parts)
        
        # Hash long keys to keep them manageable
        if len(key_string) > 100:
            return hashlib.md5(key_string.encode()).hexdigest()
        
        return key_string
    
    def get_statistics_cached(self) -> Dict[str, Any]:
        """Get overall statistics with caching."""
        cache_key = self._make_cache_key("get_statistics")
        
        # Check cache
        cached_result = self._query_cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Cache miss, compute result
        result = self.get_statistics()
        
        # Cache the result
        self._query_cache.set(cache_key, result, self._stats_cache_ttl)
        
        return result
    
    def get_dataset_stats_cached(self, dataset_name: str) -> Dict[str, Any]:
        """Get dataset statistics with caching."""
        cache_key = self._make_cache_key("get_dataset_stats", dataset_name)
        
        # Check cache
        cached_result = self._query_cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Cache miss, compute result
        result = self.get_dataset_stats(dataset_name)
        
        # Cache the result
        self._query_cache.set(cache_key, result, self._dataset_stats_cache_ttl)
        
        return result
    
    def get_recent_jobs_cached(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent jobs with short-term caching."""
        cache_key = self._make_cache_key("get_recent_jobs", limit)
        
        # Check cache (shorter TTL for recent jobs)
        cached_result = self._query_cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Cache miss, compute result
        result = self.get_recent_jobs_optimized(limit)
        
        # Cache with shorter TTL (1 minute)
        self._query_cache.set(cache_key, result, timedelta(minutes=1))
        
        return result
    
    def invalidate_cache(self, pattern: Optional[str] = None):
        """Invalidate cached queries.
        
        Args:
            pattern: If provided, invalidate only matching keys
        """
        self._query_cache.invalidate(pattern)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._query_cache.get_stats()
    
    # Override methods that modify data to invalidate relevant cache entries
    
    def create_execution(self, *args, **kwargs):
        """Create execution and invalidate relevant caches."""
        result = super().create_execution(*args, **kwargs)
        # Invalidate statistics and recent jobs cache
        self._query_cache.invalidate("get_statistics")
        self._query_cache.invalidate("get_recent_jobs")
        return result
    
    def update_execution_status(self, *args, **kwargs):
        """Update execution status and invalidate relevant caches."""
        result = super().update_execution_status(*args, **kwargs)
        if result:
            # Invalidate statistics cache
            self._query_cache.invalidate("get_statistics")
            self._query_cache.invalidate("get_recent_jobs")
        return result
    
    def batch_update_execution_status(self, *args, **kwargs):
        """Batch update and invalidate caches."""
        result = super().batch_update_execution_status(*args, **kwargs)
        if result > 0:
            self._query_cache.invalidate("get_statistics")
            self._query_cache.invalidate("get_recent_jobs")
        return result


def cached_method(ttl: timedelta = timedelta(minutes=5)):
    """Decorator to cache method results.
    
    Args:
        ttl: Time-to-live for cached results
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        # Use a simple in-memory cache per instance
        cache_attr = f"_cache_{func.__name__}"
        
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Initialize cache if not exists
            if not hasattr(self, cache_attr):
                setattr(self, cache_attr, {})
            
            cache = getattr(self, cache_attr)
            
            # Create cache key
            cache_key = str(args) + str(sorted(kwargs.items()))
            
            # Check cache
            if cache_key in cache:
                entry = cache[cache_key]
                if datetime.utcnow() < entry['expires_at']:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return entry['value']
            
            # Cache miss, compute result
            result = func(self, *args, **kwargs)
            
            # Store in cache
            cache[cache_key] = {
                'value': result,
                'expires_at': datetime.utcnow() + ttl
            }
            
            return result
        
        return wrapper
    return decorator