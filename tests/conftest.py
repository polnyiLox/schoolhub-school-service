import os
from collections.abc import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.community.postgres import PostgresContainer


os.environ.setdefault("APP_CONFIG__DB__USER", "postgres")
os.environ.setdefault("APP_CONFIG__DB__PASSWORD", "postgres")
os.environ.setdefault("APP_CONFIG__DB__HOST", "localhost")
os.environ.setdefault("APP_CONFIG__DB__PORT", "5432")
os.environ.setdefault("APP_CONFIG__DB__NAME", "school_test")
os.environ.setdefault("APP_CONFIG__API__V1_PREFIX", "/v1")
os.environ.setdefault("APP_CONFIG__API__HOST", "0.0.0.0")
os.environ.setdefault("APP_CONFIG__API__PORT", "8000")
os.environ.setdefault("APP_CONFIG__API__RELOAD", "false")
os.environ.setdefault("APP_CONFIG__MIDDLEWARE__ALLOW_ORIGINS", '["*"]')
os.environ.setdefault("APP_CONFIG__MIDDLEWARE__ALLOW_METHODS", '["*"]')
os.environ.setdefault("APP_CONFIG__MIDDLEWARE__ALLOW_HEADERS", '["*"]')
os.environ.setdefault("APP_CONFIG__MIDDLEWARE__ALLOW_CREDENTIALS", "false")


# ============================================================
# PostgreSQL
# ============================================================

@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """
    Один PostgreSQL container на весь test session.
    """

    with PostgresContainer(
        "postgres:17",
        username="test",
        password="test",
        dbname="test",
    ) as postgres:
        yield postgres


@pytest.fixture(scope="session")
def database_url(
    postgres_container: PostgresContainer,
) -> str:
    """
    Получаем URL PostgreSQL и переводим его
    с psycopg2 на asyncpg.
    """

    url = postgres_container.get_connection_url()

    return url.replace(
        "postgresql+psycopg2://",
        "postgresql+asyncpg://",
    )


# ============================================================
# Database migrations
# ============================================================

@pytest.fixture(scope="session")
def apply_migrations(database_url: str) -> None:
    """
    Применяем Alembic migrations один раз
    перед запуском integration/e2e тестов.
    """

    config = Config("alembic.ini")

    config.set_main_option(
        "sqlalchemy.url",
        database_url,
    )

    command.upgrade(config, "head")


# ============================================================
# SQLAlchemy Engine
# ============================================================

@pytest_asyncio.fixture(
    scope="session",
    loop_scope="session",
)
async def engine(
    database_url: str,
    apply_migrations: None,
) -> AsyncGenerator[AsyncEngine, None]:
    """
    Один AsyncEngine на весь test session.
    """

    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
    )

    yield engine

    await engine.dispose()


# ============================================================
# Database session
# ============================================================

@pytest_asyncio.fixture
async def session(
    engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Каждый тест получает собственную транзакцию.

    После теста транзакция откатывается,
    поэтому тесты изолированы друг от друга.
    """

    async with engine.connect() as connection:

        transaction = await connection.begin()

        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        try:
            yield session

        finally:
            await session.close()
            await transaction.rollback()
