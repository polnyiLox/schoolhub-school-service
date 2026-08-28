from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.dependencies import (
    CorrelationIdDep,
    CurrentUserDep,
    KafkaProducerDep,
    MemberServiceDep,
)
from app.api.event_publishing import execute_and_publish
from app.schemas import ClassMemberCreate, ClassMemberRead, ClassMemberUpdate

router = APIRouter(prefix="/{class_id}/members", tags=["Class members"])


@router.get("", response_model=list[ClassMemberRead])
async def list_members(
    class_id: UUID,
    actor: CurrentUserDep,
    service: MemberServiceDep,
):
    return await service.list(class_id, actor)


@router.post("", response_model=ClassMemberRead, status_code=status.HTTP_201_CREATED)
async def add_member(
    class_id: UUID,
    payload: ClassMemberCreate,
    actor: CurrentUserDep,
    service: MemberServiceDep,
    producer: KafkaProducerDep,
    correlation_id: CorrelationIdDep = None,
):
    return await execute_and_publish(
        service.add(class_id, payload, actor, correlation_id),
        service,
        producer,
        correlation_id,
    )


@router.patch("/{telegram_id}", response_model=ClassMemberRead)
async def update_member(
    class_id: UUID,
    telegram_id: int,
    payload: ClassMemberUpdate,
    actor: CurrentUserDep,
    service: MemberServiceDep,
    producer: KafkaProducerDep,
    correlation_id: CorrelationIdDep = None,
):
    return await execute_and_publish(
        service.update(class_id, telegram_id, payload, actor),
        service,
        producer,
        correlation_id,
    )


@router.delete("/{telegram_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_member(
    class_id: UUID,
    telegram_id: int,
    actor: CurrentUserDep,
    service: MemberServiceDep,
    producer: KafkaProducerDep,
    correlation_id: CorrelationIdDep = None,
) -> Response:
    await execute_and_publish(
        service.delete(class_id, telegram_id, actor),
        service,
        producer,
        correlation_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
