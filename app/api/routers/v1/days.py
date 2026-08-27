from datetime import date as date_type
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path

from app.api.dependencies import CurrentUserDep, DayServiceDep
from app.schemas import ClassDayRead

router = APIRouter(prefix="/{class_id}/days", tags=["Class day"])


@router.get("/{date}", response_model=ClassDayRead)
async def get_class_day(
    class_id: UUID,
    target_date: Annotated[date_type, Path(alias="date")],
    actor: CurrentUserDep,
    service: DayServiceDep,
):
    return await service.get(class_id, target_date, actor)
