from app.core.config import settings

from .base import Cache
from .keys import CacheKeyBuilder, CacheNamespace
from .redis import RedisCache


redis_cache = RedisCache(
    settings=settings.redis
)
cache_key_builder = CacheKeyBuilder(settings.redis.key_prefix)


__all__ = [
    "Cache",
    "CacheKeyBuilder",
    "CacheNamespace",
    "RedisCache",
    "cache_key_builder",
    "redis_cache",
]
