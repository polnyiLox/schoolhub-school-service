import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.cache import CacheKeyBuilder, CacheNamespace, RedisCache
from app.core.config import RedisSettings


def redis_client() -> MagicMock:
    client = MagicMock()
    client.ping = AsyncMock()
    client.aclose = AsyncMock()
    client.get = AsyncMock(return_value=b"value")
    client.set = AsyncMock()
    client.delete = AsyncMock(return_value=2)
    return client


def test_cache_key_builder_encodes_dynamic_parts() -> None:
    builder = CacheKeyBuilder("school service")

    key = builder.build(CacheNamespace.HOMEWORK, "class:id", "item/1")

    assert key == "school%20service:v1:homework:class%3Aid:item%2F1"
    assert builder.pattern(CacheNamespace.HOMEWORK_LIST, "class:id") == (
        "school%20service:v1:homework-list:class%3Aid:*"
    )


@pytest.mark.asyncio
async def test_redis_cache_connects_once_for_concurrent_calls(monkeypatch) -> None:
    client = redis_client()
    factory = MagicMock(return_value=client)
    monkeypatch.setattr("app.cache.redis.Redis.from_url", factory)
    cache = RedisCache(RedisSettings())

    await asyncio.gather(cache.connect(), cache.connect())

    factory.assert_called_once()
    client.ping.assert_awaited_once()


@pytest.mark.asyncio
async def test_redis_cache_uses_default_ttl_and_lazy_connection(monkeypatch) -> None:
    client = redis_client()
    monkeypatch.setattr("app.cache.redis.Redis.from_url", MagicMock(return_value=client))
    cache = RedisCache(RedisSettings(default_ttl_seconds=120))

    assert await cache.get("key") == b"value"
    await cache.set("key", b"value")

    client.get.assert_awaited_once_with("key")
    client.set.assert_awaited_once_with("key", b"value", ex=120)


@pytest.mark.asyncio
async def test_redis_cache_deletes_keys_found_by_pattern(monkeypatch) -> None:
    client = redis_client()

    async def scan_iter(**_: object):
        for key in (b"key:1", b"key:2"):
            yield key

    client.scan_iter = scan_iter
    monkeypatch.setattr("app.cache.redis.Redis.from_url", MagicMock(return_value=client))
    cache = RedisCache(RedisSettings())

    deleted = await cache.delete_pattern("key:*")

    assert deleted == 2
    client.delete.assert_awaited_once_with(b"key:1", b"key:2")


@pytest.mark.asyncio
async def test_redis_cache_deletes_large_patterns_in_bounded_batches(monkeypatch) -> None:
    client = redis_client()

    async def scan_iter(**_: object):
        for index in range(205):
            yield f"key:{index}".encode()

    client.scan_iter = scan_iter
    client.delete.side_effect = lambda *keys: len(keys)
    monkeypatch.setattr("app.cache.redis.Redis.from_url", MagicMock(return_value=client))
    cache = RedisCache(RedisSettings(scan_batch_size=100))

    assert await cache.delete_pattern("key:*") == 205
    assert [len(call.args) for call in client.delete.await_args_list] == [100, 100, 5]


@pytest.mark.asyncio
async def test_redis_cache_rejects_non_positive_explicit_ttl(monkeypatch) -> None:
    client = redis_client()
    monkeypatch.setattr("app.cache.redis.Redis.from_url", MagicMock(return_value=client))
    cache = RedisCache(RedisSettings())

    with pytest.raises(ValueError, match="greater than zero"):
        await cache.set("key", b"value", ttl_seconds=0)

    client.set.assert_not_awaited()
