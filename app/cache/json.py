import logging
from typing import TypeVar

from pydantic import TypeAdapter, ValidationError

from .base import Cache
from .keys import CacheKeyBuilder, CacheNamespace


logger = logging.getLogger(__name__)
T = TypeVar("T")


class JsonCache:
    """Typed JSON facade that keeps cache failures outside business operations."""

    def __init__(self, cache: Cache, keys: CacheKeyBuilder) -> None:
        self._cache = cache
        self._keys = keys

    async def get(
        self,
        namespace: CacheNamespace,
        *parts: object,
        adapter: TypeAdapter[T],
    ) -> T | None:
        key = self._keys.build(namespace, *parts)
        try:
            payload = await self._cache.get(key)
        except Exception:
            logger.exception("Cache read failed; using database: key=%s", key)
            return None

        if payload is None:
            logger.debug("Cache miss: key=%s", key)
            return None

        try:
            result = adapter.validate_json(payload)
        except ValidationError:
            logger.warning("Invalid cached payload removed: key=%s", key, exc_info=True)
            await self._safe_delete(key)
            return None

        logger.debug("Cache hit: key=%s", key)
        return result

    async def set(
        self,
        namespace: CacheNamespace,
        value: T,
        *parts: object,
        adapter: TypeAdapter[T],
    ) -> None:
        key = self._keys.build(namespace, *parts)
        try:
            await self._cache.set(key, adapter.dump_json(value))
        except Exception:
            logger.exception("Cache write failed; result remains uncached: key=%s", key)

    async def invalidate(self, namespace: CacheNamespace, *parts: object) -> None:
        key = self._keys.build(namespace, *parts)
        await self._safe_delete(key)

    async def invalidate_pattern(self, namespace: CacheNamespace, *parts: object) -> None:
        pattern = self._keys.pattern(namespace, *parts)
        try:
            deleted = await self._cache.delete_pattern(pattern)
            logger.debug("Cache invalidation completed: pattern=%s, deleted=%d", pattern, deleted)
        except Exception:
            logger.exception("Cache invalidation failed: pattern=%s", pattern)

    async def _safe_delete(self, key: str) -> None:
        try:
            await self._cache.delete(key)
        except Exception:
            logger.exception("Cache invalidation failed: key=%s", key)
