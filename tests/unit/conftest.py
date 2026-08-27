from contextlib import AbstractAsyncContextManager
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.enums import GlobalRole
from app.schemas import CurrentUser


class TransactionContext(AbstractAsyncContextManager):
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


@pytest.fixture
def transaction_session() -> MagicMock:
    session = MagicMock()
    session.begin.return_value = TransactionContext()
    return session


@pytest.fixture
def admin() -> CurrentUser:
    return CurrentUser(user_id=uuid4(), telegram_id=1, global_role=GlobalRole.ADMIN)


@pytest.fixture
def user() -> CurrentUser:
    return CurrentUser(user_id=uuid4(), telegram_id=2, global_role=GlobalRole.USER)
