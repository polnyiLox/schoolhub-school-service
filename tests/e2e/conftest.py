from uuid import uuid4
from unittest.mock import AsyncMock

import httpx
import pytest_asyncio

from app.db.session import get_session
from app.main import app


def gateway_headers(telegram_id: int, role: str = "user") -> dict[str, str]:
    return {
        "X-User-ID": str(uuid4()),
        "X-Telegram-ID": str(telegram_id),
        "X-Global-Role": role,
    }


@pytest_asyncio.fixture
async def e2e_client(session):
    async def session_override():
        yield session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_kafka_producer] = lambda: AsyncMock()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
from app.api.dependencies import get_kafka_producer
