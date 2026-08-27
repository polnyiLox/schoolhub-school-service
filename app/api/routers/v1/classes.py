from uuid import UUID

from fastapi import APIRouter, status

from app.api.dependencies import ClassServiceDep, CorrelationIdDep, CurrentUserDep
from app.schemas import SchoolClassCreate, SchoolClassRead, SchoolClassUpdate

from .days import router as days_router
from .homeworks import router as homeworks_router
from .members import router as members_router
from .schedule import router as schedule_router
from .school_events import router as school_events_router
from .subjects import router as subjects_router

router = APIRouter(prefix="/classes", tags=["Classes"])


@router.post("", response_model=SchoolClassRead, status_code=status.HTTP_201_CREATED)
async def create_class(
    payload: SchoolClassCreate,
    actor: CurrentUserDep,
    service: ClassServiceDep,
    correlation_id: CorrelationIdDep = None,
):
    return await service.create(payload, actor, correlation_id)


@router.get("", response_model=list[SchoolClassRead])
async def list_classes(actor: CurrentUserDep, service: ClassServiceDep):
    return await service.list(actor)


@router.get("/{class_id}", response_model=SchoolClassRead)
async def get_class(
    class_id: UUID,
    actor: CurrentUserDep,
    service: ClassServiceDep,
):
    return await service.get(class_id, actor)


@router.patch("/{class_id}", response_model=SchoolClassRead)
async def update_class(
    class_id: UUID,
    payload: SchoolClassUpdate,
    actor: CurrentUserDep,
    service: ClassServiceDep,
):
    return await service.update(class_id, payload, actor)


router.include_router(members_router)
router.include_router(subjects_router)
router.include_router(schedule_router)
router.include_router(homeworks_router)
router.include_router(school_events_router)
router.include_router(days_router)
