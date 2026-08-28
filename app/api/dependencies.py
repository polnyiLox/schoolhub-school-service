from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.broker import KafkaProducer, kafka_producer
from app.cache import JsonCache, json_cache
from app.db.session import get_session
from app.enums import GlobalRole
from app.repositories import (
    ClassMemberRepository,
    HomeworkRepository,
    ScheduleRepository,
    SchoolClassRepository,
    SchoolEventRepository,
    SubjectRepository,
)
from app.schemas import CurrentUser
from app.services import (
    ClassAccessService,
    ClassDayService,
    ClassMemberService,
    HomeworkService,
    ScheduleService,
    SchoolClassService,
    SchoolEventService,
    SubjectService,
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    gateway_user_id: Annotated[UUID, Header(alias="X-User-ID")],
    gateway_telegram_id: Annotated[int, Header(alias="X-Telegram-ID")],
    gateway_global_role: Annotated[GlobalRole, Header(alias="X-Global-Role")],
) -> CurrentUser:
    """Consume identity headers that the API Gateway has already authenticated."""
    return CurrentUser(
        user_id=gateway_user_id,
        telegram_id=gateway_telegram_id,
        global_role=gateway_global_role,
    )


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
CorrelationIdDep = Annotated[str | None, Header(alias="X-Correlation-ID")]


def get_kafka_producer() -> KafkaProducer:
    return kafka_producer


KafkaProducerDep = Annotated[KafkaProducer, Depends(get_kafka_producer)]


def get_json_cache() -> JsonCache:
    return json_cache


JsonCacheDep = Annotated[JsonCache, Depends(get_json_cache)]


def get_class_repository(session: SessionDep) -> SchoolClassRepository:
    return SchoolClassRepository(session)


def get_member_repository(session: SessionDep) -> ClassMemberRepository:
    return ClassMemberRepository(session)


def get_subject_repository(session: SessionDep) -> SubjectRepository:
    return SubjectRepository(session)


def get_schedule_repository(session: SessionDep) -> ScheduleRepository:
    return ScheduleRepository(session)


def get_homework_repository(session: SessionDep) -> HomeworkRepository:
    return HomeworkRepository(session)


def get_event_repository(session: SessionDep) -> SchoolEventRepository:
    return SchoolEventRepository(session)


ClassRepoDep = Annotated[SchoolClassRepository, Depends(get_class_repository)]
MemberRepoDep = Annotated[ClassMemberRepository, Depends(get_member_repository)]
SubjectRepoDep = Annotated[SubjectRepository, Depends(get_subject_repository)]
ScheduleRepoDep = Annotated[ScheduleRepository, Depends(get_schedule_repository)]
HomeworkRepoDep = Annotated[HomeworkRepository, Depends(get_homework_repository)]
EventRepoDep = Annotated[SchoolEventRepository, Depends(get_event_repository)]


def get_access_service(class_repo: ClassRepoDep, member_repo: MemberRepoDep) -> ClassAccessService:
    return ClassAccessService(class_repo, member_repo)


AccessDep = Annotated[ClassAccessService, Depends(get_access_service)]


def get_class_service(session: SessionDep, repo: ClassRepoDep, access: AccessDep) -> SchoolClassService:
    return SchoolClassService(session, repo, access)


def get_member_service(
    session: SessionDep, repo: MemberRepoDep, class_repo: ClassRepoDep, access: AccessDep
) -> ClassMemberService:
    return ClassMemberService(session, repo, class_repo, access)


def get_subject_service(
    session: SessionDep, repo: SubjectRepoDep, access: AccessDep, cache: JsonCacheDep,
) -> SubjectService:
    return SubjectService(session, repo, access, cache)


def get_schedule_service(
    session: SessionDep, repo: ScheduleRepoDep, subject_repo: SubjectRepoDep,
    access: AccessDep, cache: JsonCacheDep,
) -> ScheduleService:
    return ScheduleService(session, repo, subject_repo, access, cache)


def get_homework_service(
    session: SessionDep, repo: HomeworkRepoDep, subject_repo: SubjectRepoDep,
    access: AccessDep, cache: JsonCacheDep,
) -> HomeworkService:
    return HomeworkService(session, repo, subject_repo, access, cache)


def get_event_service(session: SessionDep, repo: EventRepoDep, access: AccessDep) -> SchoolEventService:
    return SchoolEventService(session, repo, access)


ClassServiceDep = Annotated[SchoolClassService, Depends(get_class_service)]
MemberServiceDep = Annotated[ClassMemberService, Depends(get_member_service)]
SubjectServiceDep = Annotated[SubjectService, Depends(get_subject_service)]
ScheduleServiceDep = Annotated[ScheduleService, Depends(get_schedule_service)]
HomeworkServiceDep = Annotated[HomeworkService, Depends(get_homework_service)]
EventServiceDep = Annotated[SchoolEventService, Depends(get_event_service)]


def get_day_service(
    schedule: ScheduleServiceDep, homework_repo: HomeworkRepoDep,
    event_repo: EventRepoDep, access: AccessDep,
) -> ClassDayService:
    return ClassDayService(schedule, homework_repo, event_repo, access)


DayServiceDep = Annotated[ClassDayService, Depends(get_day_service)]
