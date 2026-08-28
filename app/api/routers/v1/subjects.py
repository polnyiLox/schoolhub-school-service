from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.dependencies import (
    CorrelationIdDep,
    CurrentUserDep,
    SubjectServiceDep,
)
from app.schemas import SubjectCreate, SubjectRead, SubjectUpdate

router = APIRouter(prefix="/{class_id}/subjects", tags=["Subjects"])


@router.get("", response_model=list[SubjectRead])
async def list_subjects(
    class_id: UUID,
    actor: CurrentUserDep,
    service: SubjectServiceDep,
):
    return await service.list(class_id, actor)


@router.post("", response_model=SubjectRead, status_code=status.HTTP_201_CREATED)
async def create_subject(
    class_id: UUID,
    payload: SubjectCreate,
    actor: CurrentUserDep,
    service: SubjectServiceDep,
    correlation_id: CorrelationIdDep = None,
):
    return await service.create(class_id, payload, actor, correlation_id)


@router.patch("/{subject_id}", response_model=SubjectRead)
async def update_subject(
    class_id: UUID,
    subject_id: UUID,
    payload: SubjectUpdate,
    actor: CurrentUserDep,
    service: SubjectServiceDep,
    correlation_id: CorrelationIdDep = None,
):
    return await service.update(class_id, subject_id, payload, actor, correlation_id)


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subject(
    class_id: UUID,
    subject_id: UUID,
    actor: CurrentUserDep,
    service: SubjectServiceDep,
    correlation_id: CorrelationIdDep = None,
) -> Response:
    await service.delete(class_id, subject_id, actor, correlation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
