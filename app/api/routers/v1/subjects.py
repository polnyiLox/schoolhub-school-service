from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.dependencies import CurrentUserDep, KafkaProducerDep, SubjectServiceDep
from app.api.event_publishing import execute_and_publish
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
    producer: KafkaProducerDep,
):
    return await execute_and_publish(
        service.create(class_id, payload, actor),
        service,
        producer,
    )


@router.patch("/{subject_id}", response_model=SubjectRead)
async def update_subject(
    class_id: UUID,
    subject_id: UUID,
    payload: SubjectUpdate,
    actor: CurrentUserDep,
    service: SubjectServiceDep,
    producer: KafkaProducerDep,
):
    return await execute_and_publish(
        service.update(class_id, subject_id, payload, actor),
        service,
        producer,
    )


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subject(
    class_id: UUID,
    subject_id: UUID,
    actor: CurrentUserDep,
    service: SubjectServiceDep,
    producer: KafkaProducerDep,
) -> Response:
    await execute_and_publish(
        service.delete(class_id, subject_id, actor),
        service,
        producer,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
