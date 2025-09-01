"""
Caching service for ORM Capital Calculator Engine

Provides Redis-based caching for production and in-memory caching for development
with configurable TTL management and cache invalidation strategies.
"""

import json
import pickle
import hashlib
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

import redis.asyncio as redis
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from orm_calculator.models.pydantic_models import CalculationResult


class CacheType(str, Enum):
    """Cache implementation types"""
    MEMORY = "memory"
    REDIS = "redis"


class CacheConfig(BaseSettings):
    """Cache configuration settings"""
    cache_type: CacheType = CacheType.MEMORY
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_ssl: bool = False
    default_ttl: int = 3600  # 1 hour default TTL
    max_memory_cache_size: int = 1000  # Max items in memory cache
    
    class Config:
        env_prefix = "CACHE_"


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: Optional[datetime] = None


class CacheKeyBuilder:
    """Utility for building consistent cache keys"""
    
    @staticmethod
    def calculation_result(entity_id: str, calculation_date: str, model_name: str, 
                          parameters_hash: str) -> str:
        """Build cache key for calculation results"""
        key_data = f"calc:{entity_id}:{calculation_date}:{model_name}:{parameters_hash}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    @staticmethod
    def parameter_set(model_name: str, version_id: str) -> str:
        """Build cache key for parameter sets"""
        return f"params:{model_name}:{version_id}"
    
    @staticmethod
    def business_indicator(entity_id: str, period: str) -> str:
        """Build cache key for business indicators"""
        return f"bi:{entity_id}:{period}"
    
    @staticmethod
    def loss_data(entity_id: str, start_date: str, end_date: str) -> str:
        """Build cache key for loss data queries"""
        key_data = f"loss:{entity_id}:{start_date}:{end_date}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    @staticmethod
    def query_result(query_hash: str, params_hash: str) -> str:
        """Build cache key for database query results"""
        return f"query:{query_hash}:{params_hash}"


class CacheService(ABC):
    """Abstract cache service interface"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete value from cache"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        pass
    
    @abstractmethod
    async def clear(self, pattern: Optional[str] = None) -> None:
        """Clear cache entries matching pattern"""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        pass


class MemoryCacheService(CacheService):
    """In-memory cache service for development"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "evictions": 0
        }
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache"""
        if key not in self._cache:
            self._stats["misses"] += 1
            return None
        
        entry = self._cache[key]
        
        # Check expiration
        if entry.expires_at and datetime.utcnow() > entry.expires_at:
            await self.delete(key)
            self._stats["misses"] += 1
            return None
        
        # Update access metadata
        entry.access_count += 1
        entry.last_accessed = datetime.utcnow()
        self._stats["hits"] += 1
        
        return entry.value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in memory cache"""
        # Evict if at capacity
        if len(self._cache) >= self.config.max_memory_cache_size:
            await self._evict_lru()
        
        expires_at = None
        if ttl:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        elif self.config.default_ttl:
            expires_at = datetime.utcnow() + timedelta(seconds=self.config.default_ttl)
        
        self._cache[key] = CacheEntry(
            value=value,
            created_at=datetime.utcnow(),
            expires_at=expires_at
        )
        self._stats["sets"] += 1
    
    async def delete(self, key: str) -> None:
        """Delete value from memory cache"""
        if key in self._cache:
            del self._cache[key]
            self._stats["deletes"] += 1
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in memory cache"""
        if key not in self._cache:
            return False
        
        entry = self._cache[key]
        if entry.expires_at and datetime.utcnow() > entry.expires_at:
            await self.delete(key)
            return False
        
        return True
    
    async def clear(self, pattern: Optional[str] = None) -> None:
        """Clear memory cache entries"""
        if pattern is None:
            self._cache.clear()
        else:
            # Simple pattern matching (prefix-based)
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(pattern.rstrip('*'))]
            for key in keys_to_delete:
                await self.delete(key)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory cache statistics"""
        return {
            **self._stats,
            "size": len(self._cache),
            "max_size": self.config.max_memory_cache_size,
            "hit_rate": self._stats["hits"] / (self._stats["hits"] + self._stats["misses"]) 
                       if (self._stats["hits"] + self._stats["misses"]) > 0 else 0
        }
    
    async def _evict_lru(self) -> None:
        """Evict least recently used entry"""
        if not self._cache:
            return
        
        # Find LRU entry
        lru_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed or self._cache[k].created_at
        )
        
        await self.delete(lru_key)
        self._stats["evictions"] += 1


class RedisCacheService(CacheService):
    """Redis-based cache service for production"""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self._redis: Optional[redis.Redis] = None
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }
    
    async def initialize(self) -> None:
        """Initialize Redis connection"""
        self._redis = redis.Redis(
            host=self.config.redis_host,
            port=self.config.redis_port,
            db=self.config.redis_db,
            password=self.config.redis_password,
            ssl=self.config.redis_ssl,
            decode_responses=False,  # We'll handle encoding ourselves
            socket_keepalive=True,
            socket_keepalive_options={},
            health_check_interval=30
        )
        
        # Test connection
        await self._redis.ping()
    
    async def close(self) -> None:
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        if not self._redis:
            raise RuntimeError("Redis not initialized")
        
        try:
            data = await self._redis.get(key)
            if data is None:
                self._stats["misses"] += 1
                return None
            
            # Deserialize data
            value = pickle.loads(data)
            self._stats["hits"] += 1
            return value
        except Exception as e:
            print(f"Redis get error for key {key}: {e}")
            self._stats["misses"] += 1
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in Redis cache"""
        if not self._redis:
            raise RuntimeError("Redis not initialized")
        
        try:
            # Serialize data
            data = pickle.dumps(value)
            
            # Set TTL
            expire_time = ttl or self.config.default_ttl
            
            await self._redis.setex(key, expire_time, data)
            self._stats["sets"] += 1
        except Exception as e:
            print(f"Redis set error for key {key}: {e}")
    
    async def delete(self, key: str) -> None:
        """Delete value from Redis cache"""
        if not self._redis:
            raise RuntimeError("Redis not initialized")
        
        try:
            await self._redis.delete(key)
            self._stats["deletes"] += 1
        except Exception as e:
            print(f"Redis delete error for key {key}: {e}")
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache"""
        if not self._redis:
            raise RuntimeError("Redis not initialized")
        
        try:
            return bool(await self._redis.exists(key))
        except Exception as e:
            print(f"Redis exists error for key {key}: {e}")
            return False
    
    async def clear(self, pattern: Optional[str] = None) -> None:
        """Clear Redis cache entries"""
        if not self._redis:
            raise RuntimeError("Redis not initialized")
        
        try:
            if pattern is None:
                await self._redis.flushdb()
            else:
                # Use SCAN to find matching keys
                keys = []
                async for key in self._redis.scan_iter(match=pattern):
                    keys.append(key)
                
                if keys:
                    await self._redis.delete(*keys)
        except Exception as e:
            print(f"Redis clear error with pattern {pattern}: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics"""
        redis_info = {}
        if self._redis:
            try:
                info = await self._redis.info()
                redis_info = {
                    "used_memory": info.get("used_memory", 0),
                    "used_memory_human": info.get("used_memory_human", "0B"),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0)
                }
            except Exception as e:
                print(f"Error getting Redis info: {e}")
        
        return {
            **self._stats,
            "redis_info": redis_info,
            "hit_rate": self._stats["hits"] / (self._stats["hits"] + self._stats["misses"]) 
                       if (self._stats["hits"] + self._stats["misses"]) > 0 else 0
        }


class CacheManager:
    """Cache manager with high-level caching operations"""
    
    def __init__(self, cache_service: CacheService):
        self.cache = cache_service
        self.key_builder = CacheKeyBuilder()
    
    async def get_calculation_result(self, entity_id: str, calculation_date: str, 
                                   model_name: str, parameters_hash: str) -> Optional[CalculationResult]:
        """Get cached calculation result"""
        key = self.key_builder.calculation_result(entity_id, calculation_date, model_name, parameters_hash)
        data = await self.cache.get(key)
        
        if data and isinstance(data, dict):
            return CalculationResult(**data)
        return None
    
    async def cache_calculation_result(self, entity_id: str, calculation_date: str, 
                                     model_name: str, parameters_hash: str, 
                                     result: CalculationResult, ttl: Optional[int] = None) -> None:
        """Cache calculation result"""
        key = self.key_builder.calculation_result(entity_id, calculation_date, model_name, parameters_hash)
        await self.cache.set(key, result.dict(), ttl)
    
    async def get_parameter_set(self, model_name: str, version_id: str) -> Optional[Dict[str, Any]]:
        """Get cached parameter set"""
        key = self.key_builder.parameter_set(model_name, version_id)
        return await self.cache.get(key)
    
    async def cache_parameter_set(self, model_name: str, version_id: str, 
                                parameters: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """Cache parameter set"""
        key = self.key_builder.parameter_set(model_name, version_id)
        await self.cache.set(key, parameters, ttl)
    
    async def get_business_indicator(self, entity_id: str, period: str) -> Optional[float]:
        """Get cached business indicator"""
        key = self.key_builder.business_indicator(entity_id, period)
        return await self.cache.get(key)
    
    async def cache_business_indicator(self, entity_id: str, period: str, 
                                     value: float, ttl: Optional[int] = None) -> None:
        """Cache business indicator"""
        key = self.key_builder.business_indicator(entity_id, period)
        await self.cache.set(key, value, ttl)
    
    async def invalidate_entity_cache(self, entity_id: str) -> None:
        """Invalidate all cache entries for an entity"""
        patterns = [
            f"calc:{entity_id}:*",
            f"bi:{entity_id}:*",
            f"loss:{entity_id}:*"
        ]
        
        for pattern in patterns:
            await self.cache.clear(pattern)
    
    async def invalidate_parameter_cache(self, model_name: str) -> None:
        """Invalidate parameter cache for a model"""
        pattern = f"params:{model_name}:*"
        await self.cache.clear(pattern)


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


async def initialize_cache(config: Optional[CacheConfig] = None) -> CacheManager:
    """Initialize cache service based on configuration"""
    global _cache_manager
    
    if config is None:
        config = CacheConfig()
    
    if config.cache_type == CacheType.REDIS:
        cache_service = RedisCacheService(config)
        await cache_service.initialize()
    else:
        cache_service = MemoryCacheService(config)
    
    _cache_manager = CacheManager(cache_service)
    return _cache_manager


async def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance"""
    if _cache_manager is None:
        return await initialize_cache()
    return _cache_manager


async def close_cache() -> None:
    """Close cache connections"""
    global _cache_manager
    if _cache_manager and hasattr(_cache_manager.cache, 'close'):
        await _cache_manager.cache.close()
    _cache_manager = None