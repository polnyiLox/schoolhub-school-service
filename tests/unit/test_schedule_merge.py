from datetime import UTC, date, datetime, time
from uuid import uuid4

from app.db.models import ScheduleEntryORM, ScheduleOverrideORM, SubjectORM
from app.enums import ScheduleLessonStatus, ScheduleOverrideType
from app.services.schedule import merge_schedule


def subject(name: str) -> SubjectORM:
    now = datetime.now(UTC)
    return SubjectORM(
        id=uuid4(), class_id=uuid4(), name=name, teacher_name=None, created_at=now, updated_at=now
    )


def entry(number: int, lesson_subject: SubjectORM) -> ScheduleEntryORM:
    return ScheduleEntryORM(
        id=uuid4(),
        class_id=lesson_subject.class_id,
        subject_id=lesson_subject.id,
        weekday=0,
        lesson_number=number,
        start_time=time(8 + number),
        end_time=time(8 + number, 45),
        room="101",
        subject=lesson_subject,
    )


def override(
    number: int, kind: ScheduleOverrideType, lesson_subject: SubjectORM | None = None
) -> ScheduleOverrideORM:
    return ScheduleOverrideORM(
        id=uuid4(),
        class_id=uuid4(),
        date=date(2026, 9, 14),
        lesson_number=number,
        override_type=kind,
        subject_id=lesson_subject.id if lesson_subject else None,
        start_time=None,
        end_time=None,
        room=None,
        reason="change",
        created_by_telegram_id=1,
        subject=lesson_subject,
    )


def test_merge_keeps_normal_lesson():
    math = subject("Math")
    result = merge_schedule(date(2026, 9, 14), [entry(1, math)], [])
    assert result.lessons[0].status == ScheduleLessonStatus.NORMAL
    assert result.lessons[0].subject.name == "Math"


def test_merge_replaces_subject_and_inherits_time():
    math, history = subject("Math"), subject("History")
    result = merge_schedule(
        date(2026, 9, 14), [entry(2, math)], [override(2, ScheduleOverrideType.REPLACED, history)]
    )
    assert result.lessons[0].subject.name == "History"
    assert result.lessons[0].start_time == time(10)
    assert result.lessons[0].status == ScheduleLessonStatus.REPLACED


def test_merge_keeps_cancelled_lesson_visible():
    english = subject("English")
    result = merge_schedule(
        date(2026, 9, 14), [entry(3, english)], [override(3, ScheduleOverrideType.CANCELLED)]
    )
    assert result.lessons[0].subject.name == "English"
    assert result.lessons[0].status == ScheduleLessonStatus.CANCELLED


def test_merge_adds_and_sorts_new_lesson():
    math, biology = subject("Math"), subject("Biology")
    result = merge_schedule(
        date(2026, 9, 14), [entry(1, math)], [override(4, ScheduleOverrideType.ADDED, biology)]
    )
    assert [lesson.lesson_number for lesson in result.lessons] == [1, 4]
    assert result.lessons[1].status == ScheduleLessonStatus.ADDED
