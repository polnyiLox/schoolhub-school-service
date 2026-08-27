from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.dependencies import CorrelationIdDep, CurrentUserDep, HomeworkServiceDep
from app.schemas import HomeworkCreate, HomeworkRead, HomeworkRevisionRead, HomeworkUpdate

router = APIRouter(prefix="/{class_id}/homeworks", tags=["Homework"])


@router.get("", response_model=list[HomeworkRead])
async def list_homeworks(
    class_id: UUID,
    actor: CurrentUserDep,
    service: HomeworkServiceDep,
):
    return await service.list(class_id, actor)


@router.get("/{homework_id}", response_model=HomeworkRead)
async def get_homework(
    class_id: UUID,
    homework_id: UUID,
    actor: CurrentUserDep,
    service: HomeworkServiceDep,
):
    return await service.get(class_id, homework_id, actor)


@router.post("", response_model=HomeworkRead, status_code=status.HTTP_201_CREATED)
async def create_homework(
    class_id: UUID,
    payload: HomeworkCreate,
    actor: CurrentUserDep,
    service: HomeworkServiceDep,
    correlation_id: CorrelationIdDep = None,
):
    return await service.create(class_id, payload, actor, correlation_id)


@router.patch("/{homework_id}", response_model=HomeworkRead)
async def update_homework(
    class_id: UUID,
    homework_id: UUID,
    payload: HomeworkUpdate,
    actor: CurrentUserDep,
    service: HomeworkServiceDep,
):
    return await service.update(class_id, homework_id, payload, actor)


@router.delete("/{homework_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_homework(
    class_id: UUID,
    homework_id: UUID,
    actor: CurrentUserDep,
    service: HomeworkServiceDep,
) -> Response:
    await service.delete(class_id, homework_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{homework_id}/history", response_model=list[HomeworkRevisionRead])
async def get_homework_history(
    class_id: UUID,
    homework_id: UUID,
    actor: CurrentUserDep,
    service: HomeworkServiceDep,
):
    return await service.history(class_id, homework_id, actor)
