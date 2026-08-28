import asyncio
import logging

from redis.asyncio import Redis

from app.core.config import RedisSettings

from .base import Cache


logger = logging.getLogger(__name__)


class RedisCache(Cache):
    def __init__(self, settings: RedisSettings) -> None:
        self._redis: Redis | None = None
        self._settings = settings
        self._connect_lock = asyncio.Lock()

    async def connect(self) -> None:
        if self._redis is not None:
            return

        async with self._connect_lock:
            if self._redis is not None:
                return

            logger.debug("Connecting to Redis at %s:%d", self._settings.host, self._settings.port)
            client = Redis.from_url(self._settings.url, decode_responses=False)
            try:
                await client.ping()
            except Exception:
                logger.exception("Redis connection failed")
                await client.aclose()
                raise

            self._redis = client
            logger.info("Connected to Redis")

    async def get_redis(self) -> Redis:
        await self.connect()
        assert self._redis is not None
        return self._redis

    async def close(self) -> None:
        client = self._redis
        self._redis = None
        if client is None:
            return

        await client.aclose()
        logger.info("Closed Redis connection")

    async def get(self, key: str) -> bytes | str | None:
        client = await self.get_redis()
        logger.debug("Reading Redis key: key=%s", key)
        try:
            return await client.get(key)
        except Exception:
            logger.exception("Redis read failed: key=%s", key)
            raise

    async def set(
        self,
        key: str,
        value: str | bytes,
        ttl_seconds: int | None = None,
    ) -> None:
        client = await self.get_redis()
        ttl = self._settings.default_ttl_seconds if ttl_seconds is None else ttl_seconds
        if ttl < 1:
            raise ValueError("Redis TTL must be greater than zero")
        logger.debug("Writing Redis key: key=%s, ttl=%d", key, ttl)
        try:
            await client.set(key, value, ex=ttl)
        except Exception:
            logger.exception("Redis write failed: key=%s", key)
            raise

    async def delete(self, *keys: str) -> int:
        if not keys:
            return 0

        client = await self.get_redis()
        logger.debug("Deleting %d Redis keys", len(keys))
        try:
            return await client.delete(*keys)
        except Exception:
            logger.exception("Redis delete failed for %d keys", len(keys))
            raise

    async def delete_pattern(self, pattern: str) -> int:
        client = await self.get_redis()
        deleted = 0
        batch: list[bytes | str] = []
        try:
            async for key in client.scan_iter(
                match=pattern,
                count=self._settings.scan_batch_size,
            ):
                batch.append(key)
                if len(batch) >= self._settings.scan_batch_size:
                    deleted += await client.delete(*batch)
                    batch.clear()
            if batch:
                deleted += await client.delete(*batch)
        except Exception:
            logger.exception("Redis pattern delete failed: pattern=%s", pattern)
            raise

        logger.debug("Deleted %d Redis keys by pattern: pattern=%s", deleted, pattern)
        return deleted
