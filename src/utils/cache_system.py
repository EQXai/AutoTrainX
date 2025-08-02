"""
Intelligent caching system for AutoTrainX
"""
import asyncio
import hashlib
import json
import pickle
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar, Union
import redis
from diskcache import Cache as DiskCache

T = TypeVar('T')

class CacheBackend(ABC):
    """Abstract cache backend"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass
    
    @abstractmethod
    async def clear(self) -> bool:
        pass

class MemoryCache(CacheBackend):
    """In-memory cache backend"""
    
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, Dict] = {}
        self.max_size = max_size
    
    async def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if entry['expires_at'] and datetime.now() > entry['expires_at']:
            del self._cache[key]
            return None
        
        entry['last_accessed'] = datetime.now()
        return entry['value']
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        # Evict if at capacity
        if len(self._cache) >= self.max_size:
            self._evict_lru()
        
        expires_at = None
        if ttl:
            expires_at = datetime.now() + timedelta(seconds=ttl)
        
        self._cache[key] = {
            'value': value,
            'created_at': datetime.now(),
            'last_accessed': datetime.now(),
            'expires_at': expires_at
        }
        return True
    
    async def delete(self, key: str) -> bool:
        return self._cache.pop(key, None) is not None
    
    async def clear(self) -> bool:
        self._cache.clear()
        return True
    
    def _evict_lru(self):
        """Evict least recently used item"""
        if not self._cache:
            return
        
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k]['last_accessed']
        )
        del self._cache[oldest_key]

class RedisCache(CacheBackend):
    """Redis cache backend"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.redis = redis.Redis(host=host, port=port, db=db, decode_responses=False)
    
    async def get(self, key: str) -> Optional[Any]:
        try:
            data = self.redis.get(key)
            if data:
                return pickle.loads(data)
        except Exception:
            pass
        return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        try:
            data = pickle.dumps(value)
            if ttl:
                return self.redis.setex(key, ttl, data)
            else:
                return self.redis.set(key, data)
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        try:
            return bool(self.redis.delete(key))
        except Exception:
            return False
    
    async def clear(self) -> bool:
        try:
            self.redis.flushdb()
            return True
        except Exception:
            return False

class DiskCacheBackend(CacheBackend):
    """Disk-based cache backend"""
    
    def __init__(self, cache_dir: Path = Path("cache")):
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache = DiskCache(str(cache_dir))
    
    async def get(self, key: str) -> Optional[Any]:
        return self.cache.get(key)
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        try:
            if ttl:
                self.cache.set(key, value, expire=ttl)
            else:
                self.cache.set(key, value)
            return True
        except Exception:
            return False
    
    async def delete(self, key: str) -> bool:
        try:
            return self.cache.delete(key)
        except Exception:
            return False
    
    async def clear(self) -> bool:
        try:
            self.cache.clear()
            return True
        except Exception:
            return False

class CacheManager:
    """Main cache manager with multiple backends"""
    
    def __init__(self, 
                 primary_backend: CacheBackend,
                 fallback_backend: Optional[CacheBackend] = None):
        self.primary = primary_backend
        self.fallback = fallback_backend
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0
        }
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache with fallback"""
        # Try primary backend
        value = await self.primary.get(key)
        if value is not None:
            self.stats['hits'] += 1
            return value
        
        # Try fallback backend
        if self.fallback:
            value = await self.fallback.get(key)
            if value is not None:
                # Restore to primary cache
                await self.primary.set(key, value)
                self.stats['hits'] += 1
                return value
        
        self.stats['misses'] += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache"""
        success = await self.primary.set(key, value, ttl)
        if self.fallback and success:
            await self.fallback.set(key, value, ttl)
        
        if success:
            self.stats['sets'] += 1
        return success
    
    async def delete(self, key: str) -> bool:
        """Delete from cache"""
        success = await self.primary.delete(key)
        if self.fallback:
            await self.fallback.delete(key)
        
        if success:
            self.stats['deletes'] += 1
        return success
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests) if total_requests > 0 else 0
        
        return {
            **self.stats,
            'hit_rate': hit_rate,
            'total_requests': total_requests
        }

# Cache decorators
def cached(ttl: int = 3600, key_prefix: str = ""):
    """Decorator for caching function results"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = _generate_cache_key(func.__name__, args, kwargs, key_prefix)
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, run in event loop
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(async_wrapper(*args, **kwargs))
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def cache_invalidate(key_pattern: str):
    """Decorator to invalidate cache on function execution"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            # Invalidate cache entries matching pattern
            cache_key = _generate_cache_key(key_pattern, args, kwargs)
            await cache_manager.delete(cache_key)
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            loop = asyncio.get_event_loop()
            cache_key = _generate_cache_key(key_pattern, args, kwargs)
            loop.run_until_complete(cache_manager.delete(cache_key))
            return result
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def _generate_cache_key(func_name: str, args: tuple, kwargs: dict, prefix: str = "") -> str:
    """Generate cache key from function name and arguments"""
    # Create a hash of the arguments
    arg_string = json.dumps({
        'args': args,
        'kwargs': sorted(kwargs.items())
    }, sort_keys=True, default=str)
    
    arg_hash = hashlib.md5(arg_string.encode()).hexdigest()
    
    parts = [prefix, func_name, arg_hash]
    return ":".join(filter(None, parts))

# Global cache manager instance
cache_manager: Optional[CacheManager] = None

def setup_cache(backend_type: str = "memory", **kwargs) -> CacheManager:
    """Setup global cache manager"""
    global cache_manager
    
    if backend_type == "redis":
        primary = RedisCache(**kwargs)
        fallback = MemoryCache()
    elif backend_type == "disk":
        primary = DiskCacheBackend(**kwargs)
        fallback = MemoryCache()
    else:
        primary = MemoryCache(**kwargs)
        fallback = None
    
    cache_manager = CacheManager(primary, fallback)
    return cache_manager

# Specialized cache functions for AutoTrainX
@cached(ttl=1800, key_prefix="model_info")
async def get_model_info(model_path: str) -> Dict[str, Any]:
    """Cached model information retrieval"""
    # This would be implemented to read model metadata
    pass

@cached(ttl=3600, key_prefix="dataset_stats")
async def get_dataset_statistics(dataset_path: str) -> Dict[str, Any]:
    """Cached dataset statistics"""
    # This would be implemented to analyze dataset
    pass

@cached(ttl=300, key_prefix="job_status")
async def get_job_status(job_id: str) -> Dict[str, Any]:
    """Cached job status information"""
    # This would be implemented to check job status
    pass