import logging
from uuid import UUID

from app.db.models import ClassMemberORM
from app.enums import ClassMemberRole, GlobalRole
from app.exceptions import ClassAccessDeniedError, ClassNotFoundError
from app.repositories import ClassMemberRepository, SchoolClassRepository
from app.schemas import CurrentUser

logger = logging.getLogger(__name__)


class ClassAccessService:
    def __init__(
        self,
        class_repository: SchoolClassRepository,
        member_repository: ClassMemberRepository,
    ) -> None:
        self.class_repository = class_repository
        self.member_repository = member_repository

    async def require_member(self, class_id: UUID, actor: CurrentUser) -> ClassMemberORM | None:
        if await self.class_repository.get_by_id(class_id) is None:
            raise ClassNotFoundError()
        if actor.global_role == GlobalRole.ADMIN:
            return None
        member = await self.member_repository.get(class_id, actor.telegram_id)
        if member is None:
            logger.warning("class access denied", extra={"class_id": str(class_id), "telegram_id": actor.telegram_id})
            raise ClassAccessDeniedError()
        return member

    async def require_editor(self, class_id: UUID, actor: CurrentUser) -> ClassMemberORM | None:
        member = await self.require_member(class_id, actor)
        if actor.global_role == GlobalRole.ADMIN:
            return None
        if member is None or member.role != ClassMemberRole.EDITOR:
            logger.warning("class editor access denied", extra={"class_id": str(class_id), "telegram_id": actor.telegram_id})
            raise ClassAccessDeniedError("Editor role is required")
        return member

    def require_admin(self, actor: CurrentUser) -> None:
        if actor.global_role != GlobalRole.ADMIN:
            logger.warning("admin access denied", extra={"telegram_id": actor.telegram_id})
            raise ClassAccessDeniedError("Administrator role is required")
