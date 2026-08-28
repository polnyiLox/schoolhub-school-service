from app.core.config import settings

from .base import Cache
from .json import JsonCache
from .keys import CacheKeyBuilder, CacheNamespace
from .redis import RedisCache

redis_cache = RedisCache(settings=settings.redis)
cache_key_builder = CacheKeyBuilder(settings.redis.key_prefix)
json_cache = JsonCache(redis_cache, cache_key_builder)


__all__ = [
    "Cache",
    "CacheKeyBuilder",
    "CacheNamespace",
    "JsonCache",
    "RedisCache",
    "cache_key_builder",
    "json_cache",
    "redis_cache",
]
