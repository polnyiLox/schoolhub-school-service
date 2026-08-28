from app.core.config import settings

from .base import Cache
from .redis import RedisCache


redis_cache = RedisCache(
    settings=settings.redis
)


__all__ = [
    "Cache",
    "RedisCache",
    "redis_cache",
]
