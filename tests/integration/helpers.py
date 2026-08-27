from datetime import UTC, date, datetime, time

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ClassMemberORM, SchoolClassORM, SubjectORM
from app.enums import ClassMemberRole


async def create_class(session: AsyncSession, name: str = "10A") -> SchoolClassORM:
    entity = SchoolClassORM(name=name, academic_year="2026/2027", is_archived=False)
    session.add(entity)
    await session.flush()
    return entity


async def create_subject(session: AsyncSession, class_id, name: str = "Math") -> SubjectORM:
    entity = SubjectORM(class_id=class_id, name=name, teacher_name=None)
    session.add(entity)
    await session.flush()
    return entity


async def create_member(session: AsyncSession, class_id, telegram_id: int, role=ClassMemberRole.STUDENT) -> ClassMemberORM:
    entity = ClassMemberORM(class_id=class_id, telegram_id=telegram_id, role=role)
    session.add(entity)
    await session.flush()
    return entity


SCHOOL_DAY = date(2026, 9, 14)
LESSON_START = time(8)
LESSON_END = time(8, 45)
EVENT_START = datetime(2026, 9, 14, 10, tzinfo=UTC)
