from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.dependencies import CurrentUserDep, EventServiceDep, KafkaProducerDep
from app.api.event_publishing import execute_and_publish
from app.schemas import SchoolEventCreate, SchoolEventRead, SchoolEventUpdate

router = APIRouter(prefix="/{class_id}/events", tags=["School events"])


@router.get("", response_model=list[SchoolEventRead])
async def list_events(
    class_id: UUID,
    actor: CurrentUserDep,
    service: EventServiceDep,
):
    return await service.list(class_id, actor)


@router.get("/{event_id}", response_model=SchoolEventRead)
async def get_event(
    class_id: UUID,
    event_id: UUID,
    actor: CurrentUserDep,
    service: EventServiceDep,
):
    return await service.get(class_id, event_id, actor)


@router.post("", response_model=SchoolEventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
    class_id: UUID,
    payload: SchoolEventCreate,
    actor: CurrentUserDep,
    service: EventServiceDep,
    producer: KafkaProducerDep,
):
    return await execute_and_publish(
        service.create(class_id, payload, actor),
        service,
        producer,
    )


@router.patch("/{event_id}", response_model=SchoolEventRead)
async def update_event(
    class_id: UUID,
    event_id: UUID,
    payload: SchoolEventUpdate,
    actor: CurrentUserDep,
    service: EventServiceDep,
    producer: KafkaProducerDep,
):
    return await execute_and_publish(
        service.update(class_id, event_id, payload, actor),
        service,
        producer,
    )


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    class_id: UUID,
    event_id: UUID,
    actor: CurrentUserDep,
    service: EventServiceDep,
    producer: KafkaProducerDep,
) -> Response:
    await execute_and_publish(
        service.delete(class_id, event_id, actor),
        service,
        producer,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
