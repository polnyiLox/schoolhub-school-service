from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, File, Response, UploadFile, status

from app.api.dependencies import (
    CorrelationIdDep,
    CurrentUserDep,
    HomeworkServiceDep,
)
from app.core.config import settings
from app.schemas import (
    HomeworkAttachmentRead,
    HomeworkCreate,
    HomeworkRead,
    HomeworkRevisionRead,
    HomeworkUpdate,
)

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
    correlation_id: CorrelationIdDep = None,
):
    return await service.update(class_id, homework_id, payload, actor, correlation_id)


@router.delete("/{homework_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_homework(
    class_id: UUID,
    homework_id: UUID,
    actor: CurrentUserDep,
    service: HomeworkServiceDep,
    correlation_id: CorrelationIdDep = None,
) -> Response:
    await service.delete(class_id, homework_id, actor, correlation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{homework_id}/history", response_model=list[HomeworkRevisionRead])
async def get_homework_history(
    class_id: UUID,
    homework_id: UUID,
    actor: CurrentUserDep,
    service: HomeworkServiceDep,
):
    return await service.history(class_id, homework_id, actor)


@router.post(
    "/{homework_id}/attachments",
    response_model=HomeworkAttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_homework_attachment(
    class_id: UUID,
    homework_id: UUID,
    actor: CurrentUserDep,
    service: HomeworkServiceDep,
    file: Annotated[UploadFile, File()],
):
    content = await file.read(settings.object_storage.max_file_size_bytes + 1)
    return await service.upload_attachment(
        class_id,
        homework_id,
        file.filename or "attachment",
        file.content_type or "application/octet-stream",
        content,
        actor,
    )


@router.get("/{homework_id}/attachments", response_model=list[HomeworkAttachmentRead])
async def list_homework_attachments(
    class_id: UUID,
    homework_id: UUID,
    actor: CurrentUserDep,
    service: HomeworkServiceDep,
):
    return await service.list_attachments(class_id, homework_id, actor)


@router.get("/{homework_id}/attachments/{attachment_id}")
async def download_homework_attachment(
    class_id: UUID,
    homework_id: UUID,
    attachment_id: UUID,
    actor: CurrentUserDep,
    service: HomeworkServiceDep,
) -> Response:
    attachment, content = await service.download_attachment(
        class_id, homework_id, attachment_id, actor
    )
    encoded_name = quote(attachment.file_name, safe="")
    return Response(
        content=content,
        media_type=attachment.content_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}"},
    )


@router.delete(
    "/{homework_id}/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_homework_attachment(
    class_id: UUID,
    homework_id: UUID,
    attachment_id: UUID,
    actor: CurrentUserDep,
    service: HomeworkServiceDep,
) -> Response:
    await service.delete_attachment(class_id, homework_id, attachment_id, actor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
