from uuid import UUID

from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, model_validator

from app.enums import GlobalRole


class ORMReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class NonEmptyUpdateModel(BaseModel):
    non_nullable_fields: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        null_fields = self.model_fields_set & self.non_nullable_fields
        for field_name in null_fields:
            if getattr(self, field_name) is None:
                raise ValueError(f"Field '{field_name}' cannot be null")
        return self


class CurrentUser(BaseModel):
    user_id: UUID
    telegram_id: int
    global_role: GlobalRole
