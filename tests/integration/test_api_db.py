from datetime import date
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio

from app.db.session import get_session
from app.enums import ClassMemberRole
from app.main import app
from tests.integration.helpers import create_class, create_member, create_subject


def headers(telegram_id: int, role: str = "user") -> dict[str, str]:
    return {
        "X-User-ID": str(uuid4()),
        "X-Telegram-ID": str(telegram_id),
        "X-Global-Role": role,
    }


@pytest_asyncio.fixture
async def api_client(session):
    async def session_override():
        yield session

    app.dependency_overrides[get_session] = session_override
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_class_api_to_real_postgres(api_client):
    response = await api_client.post(
        "/v1/classes",
        json={"name": "11A", "academic_year": "2026/2027"},
        headers=headers(1, "admin"),
    )
    assert response.status_code == 201
    assert response.json()["name"] == "11A"


@pytest.mark.asyncio
async def test_create_homework_api_to_real_postgres(api_client, session):
    async with session.begin():
        school_class = await create_class(session)
        subject = await create_subject(session, school_class.id)
        await create_member(session, school_class.id, 20, ClassMemberRole.EDITOR)
    response = await api_client.post(
        f"/v1/classes/{school_class.id}/homeworks",
        json={
            "subject_id": str(subject.id),
            "assigned_date": str(date(2026, 9, 14)),
            "due_date": str(date(2026, 9, 15)),
            "text": "Exercises 1-5",
        },
        headers=headers(20),
    )
    assert response.status_code == 201
    assert response.json()["text"] == "Exercises 1-5"
