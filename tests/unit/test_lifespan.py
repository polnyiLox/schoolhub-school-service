import logging
from unittest.mock import AsyncMock

import pytest

from app.main import app, connect_cache, lifespan


@pytest.mark.asyncio
async def test_cache_connection_failure_does_not_block_startup(monkeypatch, caplog):
    connect = AsyncMock(side_effect=ConnectionError("Redis unavailable"))
    monkeypatch.setattr("app.main.redis_cache.connect", connect)

    with caplog.at_level(logging.WARNING):
        await connect_cache()

    connect.assert_awaited_once()
    assert "starting without cache" in caplog.text


@pytest.mark.asyncio
async def test_lifespan_starts_and_stops_outbox_relay(monkeypatch):
    connect = AsyncMock()
    kafka_close = AsyncMock()
    relay_start = AsyncMock()
    relay_stop = AsyncMock()
    cache_close = AsyncMock()
    storage_close = AsyncMock()
    dispose = AsyncMock()
    monkeypatch.setattr("app.main.connect_cache", connect)
    monkeypatch.setattr("app.main.kafka_client.connect_producer", AsyncMock())
    monkeypatch.setattr("app.main.kafka_client.close_producer", kafka_close)
    monkeypatch.setattr("app.main.outbox_relay.start", relay_start)
    monkeypatch.setattr("app.main.outbox_relay.stop", relay_stop)
    monkeypatch.setattr("app.main.redis_cache.close", cache_close)
    monkeypatch.setattr("app.main.object_storage.connect", AsyncMock())
    monkeypatch.setattr("app.main.object_storage.close", storage_close)
    monkeypatch.setattr("app.main.engine_dispose", dispose)

    async with lifespan(app):
        connect.assert_awaited_once()
        relay_start.assert_awaited_once()

    relay_stop.assert_awaited_once()
    kafka_close.assert_awaited_once()
    cache_close.assert_awaited_once()
    storage_close.assert_awaited_once()
    dispose.assert_awaited_once()
