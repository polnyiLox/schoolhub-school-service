import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core import health


@pytest.mark.asyncio
async def test_readiness_reports_required_dependencies(monkeypatch) -> None:
    monkeypatch.setattr(health, "check_database", AsyncMock(return_value=True))
    monkeypatch.setattr(health.kafka_client, "_producer", object())
    monkeypatch.setattr(health.outbox_relay, "_task", MagicMock(done=lambda: False))
    monkeypatch.setattr(health.redis_cache, "_redis", object())

    response = await health.readiness_handler()

    assert response.status_code == 200
    assert json.loads(response.body) == {
        "status": "ready",
        "checks": {
            "database": "up",
            "kafka": "up",
            "outbox_relay": "up",
            "redis": "up",
        },
    }


@pytest.mark.asyncio
async def test_readiness_fails_when_database_is_down(monkeypatch) -> None:
    monkeypatch.setattr(health, "check_database", AsyncMock(return_value=False))
    monkeypatch.setattr(health.kafka_client, "_producer", object())
    monkeypatch.setattr(health.outbox_relay, "_task", MagicMock(done=lambda: False))
    monkeypatch.setattr(health.redis_cache, "_redis", None)

    response = await health.readiness_handler()

    assert response.status_code == 503
    assert json.loads(response.body) == {
        "status": "unavailable",
        "checks": {
            "database": "down",
            "kafka": "up",
            "outbox_relay": "up",
            "redis": "degraded",
        },
    }


@pytest.mark.asyncio
async def test_readiness_fails_when_kafka_is_disconnected(monkeypatch) -> None:
    monkeypatch.setattr(health, "check_database", AsyncMock(return_value=True))
    monkeypatch.setattr(health.kafka_client, "_producer", None)
    monkeypatch.setattr(health.outbox_relay, "_task", MagicMock(done=lambda: False))

    response = await health.readiness_handler()

    assert response.status_code == 503
