from uuid import UUID

from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from app.enums import GlobalRole


class ORMReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class NonEmptyUpdateModel(BaseModel):
    @model_validator(mode="after")
    def require_at_least_one_field(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class CurrentUser(BaseModel):
    user_id: UUID
    telegram_id: int
    global_role: GlobalRole
