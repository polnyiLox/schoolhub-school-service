from datetime import date as date_type
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Path, Response, status

from app.api.dependencies import (
    ClassServiceDep,
    CurrentUserDep,
    DayServiceDep,
    EventServiceDep,
    HomeworkServiceDep,
    MemberServiceDep,
    ScheduleServiceDep,
    SubjectServiceDep,
)
from app.schemas import (
    ClassDayRead,
    ClassMemberCreate,
    ClassMemberRead,
    ClassMemberUpdate,
    HomeworkCreate,
    HomeworkRead,
    HomeworkRevisionRead,
    HomeworkUpdate,
    ScheduleDayRead,
    ScheduleEntryCreate,
    ScheduleEntryRead,
    ScheduleEntryUpdate,
    ScheduleOverrideCreate,
    ScheduleOverrideRead,
    ScheduleOverrideUpdate,
    ScheduleWeekRead,
    SchoolClassCreate,
    SchoolClassRead,
    SchoolClassUpdate,
    SchoolEventCreate,
    SchoolEventRead,
    SchoolEventUpdate,
    SubjectCreate,
    SubjectRead,
    SubjectUpdate,
)

router = APIRouter()
CorrelationId = Annotated[str | None, Header(alias="X-Correlation-ID")] 


@router.post("/classes", response_model=SchoolClassRead, status_code=status.HTTP_201_CREATED)
async def create_class(data: SchoolClassCreate, actor: CurrentUserDep, service: ClassServiceDep, correlation_id: CorrelationId = None):
    return await service.create(data, actor, correlation_id)


@router.get("/classes", response_model=list[SchoolClassRead])
async def list_classes(actor: CurrentUserDep, service: ClassServiceDep):
    return await service.list(actor)


@router.get("/classes/{class_id}", response_model=SchoolClassRead)
async def get_class(class_id: UUID, actor: CurrentUserDep, service: ClassServiceDep):
    return await service.get(class_id, actor)


@router.patch("/classes/{class_id}", response_model=SchoolClassRead)
async def update_class(class_id: UUID, data: SchoolClassUpdate, actor: CurrentUserDep, service: ClassServiceDep):
    return await service.update(class_id, data, actor)


@router.get("/classes/{class_id}/members", response_model=list[ClassMemberRead])
async def list_members(class_id: UUID, actor: CurrentUserDep, service: MemberServiceDep):
    return await service.list(class_id, actor)


@router.post("/classes/{class_id}/members", response_model=ClassMemberRead, status_code=status.HTTP_201_CREATED)
async def add_member(class_id: UUID, data: ClassMemberCreate, actor: CurrentUserDep, service: MemberServiceDep, correlation_id: CorrelationId = None):
    return await service.add(class_id, data, actor, correlation_id)


@router.patch("/classes/{class_id}/members/{telegram_id}", response_model=ClassMemberRead)
async def update_member(class_id: UUID, telegram_id: int, data: ClassMemberUpdate, actor: CurrentUserDep, service: MemberServiceDep):
    return await service.update(class_id, telegram_id, data, actor)


@router.delete("/classes/{class_id}/members/{telegram_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_member(class_id: UUID, telegram_id: int, actor: CurrentUserDep, service: MemberServiceDep) -> Response:
    await service.delete(class_id, telegram_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/classes/{class_id}/subjects", response_model=list[SubjectRead])
async def list_subjects(class_id: UUID, actor: CurrentUserDep, service: SubjectServiceDep):
    return await service.list(class_id, actor)


@router.post("/classes/{class_id}/subjects", response_model=SubjectRead, status_code=status.HTTP_201_CREATED)
async def create_subject(class_id: UUID, data: SubjectCreate, actor: CurrentUserDep, service: SubjectServiceDep):
    return await service.create(class_id, data, actor)


@router.patch("/classes/{class_id}/subjects/{subject_id}", response_model=SubjectRead)
async def update_subject(class_id: UUID, subject_id: UUID, data: SubjectUpdate, actor: CurrentUserDep, service: SubjectServiceDep):
    return await service.update(class_id, subject_id, data, actor)


@router.delete("/classes/{class_id}/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subject(class_id: UUID, subject_id: UUID, actor: CurrentUserDep, service: SubjectServiceDep) -> Response:
    await service.delete(class_id, subject_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/classes/{class_id}/schedule/today", response_model=ScheduleDayRead)
async def get_today_schedule(class_id: UUID, actor: CurrentUserDep, service: ScheduleServiceDep):
    return await service.get_day(class_id, date_type.today(), actor)


@router.get("/classes/{class_id}/schedule/week", response_model=ScheduleWeekRead)
async def get_week_schedule(class_id: UUID, actor: CurrentUserDep, service: ScheduleServiceDep):
    return await service.get_week(class_id, date_type.today(), actor)


@router.get("/classes/{class_id}/schedule/{date}", response_model=ScheduleDayRead)
async def get_date_schedule(class_id: UUID, target_date: Annotated[date_type, Path(alias="date")], actor: CurrentUserDep, service: ScheduleServiceDep):
    return await service.get_day(class_id, target_date, actor)


@router.post("/classes/{class_id}/schedule", response_model=ScheduleEntryRead, status_code=status.HTTP_201_CREATED)
async def create_schedule_entry(class_id: UUID, data: ScheduleEntryCreate, actor: CurrentUserDep, service: ScheduleServiceDep):
    return await service.create_entry(class_id, data, actor)


@router.patch("/classes/{class_id}/schedule/{schedule_entry_id}", response_model=ScheduleEntryRead)
async def update_schedule_entry(class_id: UUID, schedule_entry_id: UUID, data: ScheduleEntryUpdate, actor: CurrentUserDep, service: ScheduleServiceDep):
    return await service.update_entry(class_id, schedule_entry_id, data, actor)


@router.delete("/classes/{class_id}/schedule/{schedule_entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule_entry(class_id: UUID, schedule_entry_id: UUID, actor: CurrentUserDep, service: ScheduleServiceDep) -> Response:
    await service.delete_entry(class_id, schedule_entry_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/classes/{class_id}/schedule/overrides", response_model=ScheduleOverrideRead, status_code=status.HTTP_201_CREATED)
async def create_schedule_override(class_id: UUID, data: ScheduleOverrideCreate, actor: CurrentUserDep, service: ScheduleServiceDep):
    return await service.create_override(class_id, data, actor)


@router.patch("/classes/{class_id}/schedule/overrides/{override_id}", response_model=ScheduleOverrideRead)
async def update_schedule_override(class_id: UUID, override_id: UUID, data: ScheduleOverrideUpdate, actor: CurrentUserDep, service: ScheduleServiceDep):
    return await service.update_override(class_id, override_id, data, actor)


@router.delete("/classes/{class_id}/schedule/overrides/{override_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule_override(class_id: UUID, override_id: UUID, actor: CurrentUserDep, service: ScheduleServiceDep) -> Response:
    await service.delete_override(class_id, override_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/classes/{class_id}/homeworks", response_model=list[HomeworkRead])
async def list_homeworks(class_id: UUID, actor: CurrentUserDep, service: HomeworkServiceDep):
    return await service.list(class_id, actor)


@router.get("/classes/{class_id}/homeworks/{homework_id}", response_model=HomeworkRead)
async def get_homework(class_id: UUID, homework_id: UUID, actor: CurrentUserDep, service: HomeworkServiceDep):
    return await service.get(class_id, homework_id, actor)


@router.post("/classes/{class_id}/homeworks", response_model=HomeworkRead, status_code=status.HTTP_201_CREATED)
async def create_homework(class_id: UUID, data: HomeworkCreate, actor: CurrentUserDep, service: HomeworkServiceDep, correlation_id: CorrelationId = None):
    return await service.create(class_id, data, actor, correlation_id)


@router.patch("/classes/{class_id}/homeworks/{homework_id}", response_model=HomeworkRead)
async def update_homework(class_id: UUID, homework_id: UUID, data: HomeworkUpdate, actor: CurrentUserDep, service: HomeworkServiceDep):
    return await service.update(class_id, homework_id, data, actor)


@router.delete("/classes/{class_id}/homeworks/{homework_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_homework(class_id: UUID, homework_id: UUID, actor: CurrentUserDep, service: HomeworkServiceDep) -> Response:
    await service.delete(class_id, homework_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/classes/{class_id}/homeworks/{homework_id}/history", response_model=list[HomeworkRevisionRead])
async def get_homework_history(class_id: UUID, homework_id: UUID, actor: CurrentUserDep, service: HomeworkServiceDep):
    return await service.history(class_id, homework_id, actor)


@router.get("/classes/{class_id}/events", response_model=list[SchoolEventRead])
async def list_events(class_id: UUID, actor: CurrentUserDep, service: EventServiceDep):
    return await service.list(class_id, actor)


@router.get("/classes/{class_id}/events/{event_id}", response_model=SchoolEventRead)
async def get_event(class_id: UUID, event_id: UUID, actor: CurrentUserDep, service: EventServiceDep):
    return await service.get(class_id, event_id, actor)


@router.post("/classes/{class_id}/events", response_model=SchoolEventRead, status_code=status.HTTP_201_CREATED)
async def create_event(class_id: UUID, data: SchoolEventCreate, actor: CurrentUserDep, service: EventServiceDep):
    return await service.create(class_id, data, actor)


@router.patch("/classes/{class_id}/events/{event_id}", response_model=SchoolEventRead)
async def update_event(class_id: UUID, event_id: UUID, data: SchoolEventUpdate, actor: CurrentUserDep, service: EventServiceDep):
    return await service.update(class_id, event_id, data, actor)


@router.delete("/classes/{class_id}/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(class_id: UUID, event_id: UUID, actor: CurrentUserDep, service: EventServiceDep) -> Response:
    await service.delete(class_id, event_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/classes/{class_id}/days/{date}", response_model=ClassDayRead)
async def get_class_day(class_id: UUID, target_date: Annotated[date_type, Path(alias="date")], actor: CurrentUserDep, service: DayServiceDep):
    return await service.get(class_id, target_date, actor)
