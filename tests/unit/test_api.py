from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio

from app.api.dependencies import (
    get_class_service,
    get_current_user,
    get_event_service,
    get_homework_service,
    get_kafka_producer,
    get_member_service,
)
from app.db.models import HomeworkORM, SchoolClassORM
from app.enums import GlobalRole
from app.exceptions import ClassAccessDeniedError, ClassMemberAlreadyExistsError, HomeworkNotFoundError, InvalidSchoolEventDatesError
from app.main import app
from app.schemas import CurrentUser


@pytest_asyncio.fixture
async def client():
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        user_id=uuid4(), telegram_id=1, global_role=GlobalRole.ADMIN
    )
    app.dependency_overrides[get_kafka_producer] = lambda: AsyncMock()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


def class_entity():
    now = datetime.now(UTC)
    return SchoolClassORM(
        id=uuid4(), name="10A", academic_year="2026/2027", is_archived=False,
        created_at=now, updated_at=now,
    )


def service_mock() -> AsyncMock:
    service = AsyncMock()
    service.get_pending_events = MagicMock(return_value=())
    service.drain_events = MagicMock(return_value=[])
    return service


@pytest.mark.asyncio
async def test_create_class_returns_201_and_calls_service(client):
    service = service_mock()
    entity = class_entity()
    service.create.return_value = entity
    app.dependency_overrides[get_class_service] = lambda: service
    response = await client.post("/v1/classes", json={"name": "10A", "academic_year": "2026/2027"})
    assert response.status_code == 201
    assert response.json()["id"] == str(entity.id)
    service.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_academic_year_returns_422_without_service_call(client):
    service = service_mock()
    app.dependency_overrides[get_class_service] = lambda: service
    response = await client.post("/v1/classes", json={"name": "10A", "academic_year": "2026"})
    assert response.status_code == 422
    service.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_access_error_maps_to_403(client):
    service = service_mock()
    service.create.side_effect = ClassAccessDeniedError()
    app.dependency_overrides[get_class_service] = lambda: service
    response = await client.post("/v1/classes", json={"name": "10A", "academic_year": "2026/2027"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_duplicate_member_maps_to_409(client):
    service = service_mock()
    service.add.side_effect = ClassMemberAlreadyExistsError()
    app.dependency_overrides[get_member_service] = lambda: service
    response = await client.post(f"/v1/classes/{uuid4()}/members", json={"telegram_id": 20, "role": "student"})
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_missing_homework_maps_to_404(client):
    service = service_mock()
    service.get.side_effect = HomeworkNotFoundError()
    app.dependency_overrides[get_homework_service] = lambda: service
    response = await client.get(f"/v1/classes/{uuid4()}/homeworks/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_homework_response_uses_read_schema(client):
    service = service_mock()
    now = datetime.now(UTC)
    entity = HomeworkORM(
        id=uuid4(), class_id=uuid4(), subject_id=uuid4(), assigned_date=date(2026, 9, 14),
        due_date=date(2026, 9, 15), text="Task", created_by_telegram_id=1,
        updated_by_telegram_id=None, created_at=now, updated_at=now,
    )
    service.get.return_value = entity
    app.dependency_overrides[get_homework_service] = lambda: service
    response = await client.get(f"/v1/classes/{entity.class_id}/homeworks/{entity.id}")
    assert response.status_code == 200
    assert response.json()["text"] == "Task"


@pytest.mark.asyncio
async def test_domain_validation_error_maps_to_422(client):
    service = service_mock()
    service.create.side_effect = InvalidSchoolEventDatesError()
    app.dependency_overrides[get_event_service] = lambda: service
    now = datetime.now(UTC)
    response = await client.post(
        f"/v1/classes/{uuid4()}/events",
        json={"title": "Exam", "event_type": "exam", "starts_at": now.isoformat()},
    )
    assert response.status_code == 422
