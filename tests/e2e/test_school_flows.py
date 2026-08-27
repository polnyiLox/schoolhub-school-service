import pytest

from tests.e2e.conftest import gateway_headers


ADMIN = gateway_headers(1, "admin")
EDITOR = gateway_headers(20)
STUDENT = gateway_headers(30)
DAY = "2026-09-14"


async def create_class(client, name="10A"):
    response = await client.post("/v1/classes", json={"name": name, "academic_year": "2026/2027"}, headers=ADMIN)
    assert response.status_code == 201
    return response.json()["id"]


async def add_member(client, class_id, telegram_id, role):
    response = await client.post(
        f"/v1/classes/{class_id}/members",
        json={"telegram_id": telegram_id, "role": role}, headers=ADMIN,
    )
    assert response.status_code == 201


async def create_subject(client, class_id, name):
    response = await client.post(
        f"/v1/classes/{class_id}/subjects", json={"name": name}, headers=ADMIN
    )
    assert response.status_code == 201
    return response.json()["id"]


async def create_schedule(client, class_id, subject_id, number=1):
    response = await client.post(
        f"/v1/classes/{class_id}/schedule",
        json={
            "subject_id": subject_id, "weekday": 0, "lesson_number": number,
            "start_time": "08:00:00", "end_time": "08:45:00", "room": "203",
        },
        headers=ADMIN,
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_class_to_student_day_flow(e2e_client):
    class_id = await create_class(e2e_client)
    await add_member(e2e_client, class_id, 20, "editor")
    await add_member(e2e_client, class_id, 30, "student")
    subject_id = await create_subject(e2e_client, class_id, "Mathematics")
    await create_schedule(e2e_client, class_id, subject_id)
    homework = await e2e_client.post(
        f"/v1/classes/{class_id}/homeworks",
        json={"subject_id": subject_id, "assigned_date": DAY, "due_date": "2026-09-15", "text": "№125-130"},
        headers=EDITOR,
    )
    assert homework.status_code == 201
    day = await e2e_client.get(f"/v1/classes/{class_id}/days/{DAY}", headers=STUDENT)
    assert day.status_code == 200
    assert day.json()["lessons"][0]["subject"]["name"] == "Mathematics"
    assert day.json()["lessons"][0]["homeworks"][0]["text"] == "№125-130"


@pytest.mark.asyncio
async def test_replaced_schedule_override_flow(e2e_client):
    class_id = await create_class(e2e_client, "10B")
    await add_member(e2e_client, class_id, 30, "student")
    physics_id = await create_subject(e2e_client, class_id, "Physics")
    history_id = await create_subject(e2e_client, class_id, "History")
    await create_schedule(e2e_client, class_id, physics_id, 2)
    override = await e2e_client.post(
        f"/v1/classes/{class_id}/schedule/overrides",
        json={"date": DAY, "lesson_number": 2, "override_type": "replaced", "subject_id": history_id},
        headers=ADMIN,
    )
    assert override.status_code == 201
    schedule = await e2e_client.get(f"/v1/classes/{class_id}/schedule/{DAY}", headers=STUDENT)
    assert schedule.status_code == 200
    assert schedule.json()["lessons"][0]["subject"]["name"] == "History"
    assert schedule.json()["lessons"][0]["status"] == "replaced"


@pytest.mark.asyncio
async def test_homework_revision_history_flow(e2e_client):
    class_id = await create_class(e2e_client, "11A")
    await add_member(e2e_client, class_id, 20, "editor")
    await add_member(e2e_client, class_id, 30, "student")
    subject_id = await create_subject(e2e_client, class_id, "English")
    created = await e2e_client.post(
        f"/v1/classes/{class_id}/homeworks",
        json={"subject_id": subject_id, "assigned_date": DAY, "due_date": "2026-09-15", "text": "Old task"},
        headers=EDITOR,
    )
    homework_id = created.json()["id"]
    updated = await e2e_client.patch(
        f"/v1/classes/{class_id}/homeworks/{homework_id}", json={"text": "New task"}, headers=EDITOR
    )
    assert updated.status_code == 200
    history = await e2e_client.get(
        f"/v1/classes/{class_id}/homeworks/{homework_id}/history", headers=STUDENT
    )
    assert history.status_code == 200
    assert history.json()[0]["old_text"] == "Old task"
    assert history.json()[0]["new_text"] == "New task"
