import logging
from unittest.mock import AsyncMock

import pytest

from app.main import connect_cache


@pytest.mark.asyncio
async def test_cache_connection_failure_does_not_block_startup(monkeypatch, caplog):
    connect = AsyncMock(side_effect=ConnectionError("Redis unavailable"))
    monkeypatch.setattr("app.main.redis_cache.connect", connect)

    with caplog.at_level(logging.WARNING):
        await connect_cache()

    connect.assert_awaited_once()
    assert "starting without cache" in caplog.text
