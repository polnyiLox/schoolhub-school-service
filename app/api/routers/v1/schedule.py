from datetime import date as date_type
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Response, status

from app.api.dependencies import CurrentUserDep, ScheduleServiceDep
from app.schemas import (
    ScheduleDayRead,
    ScheduleEntryCreate,
    ScheduleEntryRead,
    ScheduleEntryUpdate,
    ScheduleOverrideCreate,
    ScheduleOverrideRead,
    ScheduleOverrideUpdate,
    ScheduleWeekRead,
)

router = APIRouter(prefix="/{class_id}/schedule", tags=["Schedule"])


@router.get("/today", response_model=ScheduleDayRead)
async def get_today_schedule(
    class_id: UUID,
    actor: CurrentUserDep,
    service: ScheduleServiceDep,
):
    return await service.get_day(class_id, date_type.today(), actor)


@router.get("/week", response_model=ScheduleWeekRead)
async def get_week_schedule(
    class_id: UUID,
    actor: CurrentUserDep,
    service: ScheduleServiceDep,
):
    return await service.get_week(class_id, date_type.today(), actor)


@router.get("/{date}", response_model=ScheduleDayRead)
async def get_date_schedule(
    class_id: UUID,
    target_date: Annotated[date_type, Path(alias="date")],
    actor: CurrentUserDep,
    service: ScheduleServiceDep,
):
    return await service.get_day(class_id, target_date, actor)


@router.post("", response_model=ScheduleEntryRead, status_code=status.HTTP_201_CREATED)
async def create_schedule_entry(
    class_id: UUID,
    payload: ScheduleEntryCreate,
    actor: CurrentUserDep,
    service: ScheduleServiceDep,
):
    return await service.create_entry(class_id, payload, actor)


@router.patch("/{schedule_entry_id}", response_model=ScheduleEntryRead)
async def update_schedule_entry(
    class_id: UUID,
    schedule_entry_id: UUID,
    payload: ScheduleEntryUpdate,
    actor: CurrentUserDep,
    service: ScheduleServiceDep,
):
    return await service.update_entry(class_id, schedule_entry_id, payload, actor)


@router.delete("/{schedule_entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule_entry(
    class_id: UUID,
    schedule_entry_id: UUID,
    actor: CurrentUserDep,
    service: ScheduleServiceDep,
) -> Response:
    await service.delete_entry(class_id, schedule_entry_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/overrides",
    response_model=ScheduleOverrideRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule_override(
    class_id: UUID,
    payload: ScheduleOverrideCreate,
    actor: CurrentUserDep,
    service: ScheduleServiceDep,
):
    return await service.create_override(class_id, payload, actor)


@router.patch("/overrides/{override_id}", response_model=ScheduleOverrideRead)
async def update_schedule_override(
    class_id: UUID,
    override_id: UUID,
    payload: ScheduleOverrideUpdate,
    actor: CurrentUserDep,
    service: ScheduleServiceDep,
):
    return await service.update_override(class_id, override_id, payload, actor)


@router.delete("/overrides/{override_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule_override(
    class_id: UUID,
    override_id: UUID,
    actor: CurrentUserDep,
    service: ScheduleServiceDep,
) -> Response:
    await service.delete_override(class_id, override_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
