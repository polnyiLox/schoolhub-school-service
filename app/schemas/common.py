from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.enums import GlobalRole


class ORMReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CurrentUser(BaseModel):
    user_id: UUID
    telegram_id: int
    global_role: GlobalRole
