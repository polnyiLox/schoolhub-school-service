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
