import pytest
from pydantic import ValidationError

from app.schemas import (
    HomeworkUpdate,
    ScheduleEntryUpdate,
    ScheduleOverrideUpdate,
    SchoolClassUpdate,
    SchoolEventUpdate,
    SubjectUpdate,
)


@pytest.mark.parametrize(
    "schema",
    [
        SchoolClassUpdate,
        SubjectUpdate,
        ScheduleEntryUpdate,
        ScheduleOverrideUpdate,
        HomeworkUpdate,
        SchoolEventUpdate,
    ],
)
def test_empty_update_payload_is_rejected(schema) -> None:
    with pytest.raises(ValidationError, match="At least one field"):
        schema()


def test_explicit_null_is_a_valid_nullable_field_update() -> None:
    update = SubjectUpdate(teacher_name=None)

    assert update.model_dump(exclude_unset=True) == {"teacher_name": None}


@pytest.mark.parametrize(
    ("schema", "field_name"),
    [
        (SchoolClassUpdate, "name"),
        (SchoolClassUpdate, "academic_year"),
        (SchoolClassUpdate, "is_archived"),
        (SubjectUpdate, "name"),
        (ScheduleEntryUpdate, "subject_id"),
        (ScheduleEntryUpdate, "weekday"),
        (ScheduleEntryUpdate, "lesson_number"),
        (ScheduleEntryUpdate, "start_time"),
        (ScheduleEntryUpdate, "end_time"),
        (ScheduleOverrideUpdate, "date"),
        (ScheduleOverrideUpdate, "lesson_number"),
        (ScheduleOverrideUpdate, "override_type"),
        (HomeworkUpdate, "subject_id"),
        (HomeworkUpdate, "assigned_date"),
        (HomeworkUpdate, "due_date"),
        (HomeworkUpdate, "text"),
        (SchoolEventUpdate, "title"),
        (SchoolEventUpdate, "event_type"),
        (SchoolEventUpdate, "starts_at"),
    ],
)
def test_explicit_null_is_rejected_for_non_nullable_fields(schema, field_name) -> None:
    with pytest.raises(ValidationError, match=f"Field '{field_name}' cannot be null"):
        schema(**{field_name: None})
