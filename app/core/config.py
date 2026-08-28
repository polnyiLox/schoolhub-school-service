from functools import lru_cache
from typing import Literal
from urllib.parse import quote

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DataBaseSettings(BaseModel):
    user: str = Field(min_length=1)
    password: str = Field(min_length=1)
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65_535)
    name: str = Field(min_length=1)
    pool_size: int = Field(default=10, ge=1)
    max_overflow: int = Field(default=20, ge=0)
    pool_recycle_seconds: int = Field(default=1_800, ge=1)

    @property
    def url(self) -> str:
        user = quote(self.user, safe="")
        password = quote(self.password, safe="")
        database = quote(self.name, safe="")
        return f"postgresql+asyncpg://{user}:{password}@{self.host}:{self.port}/{database}"


class ApiSettings(BaseModel):
    v1_prefix: str = Field(pattern=r"^/[^/].*$")
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65_535)
    reload: bool


class MiddlewareSettings(BaseModel):
    allow_origins: list[str]
    allow_methods: list[str]
    allow_headers: list[str]
    allow_credentials: bool


class KafkaSettings(BaseModel):
    bootstrap_servers: str = Field(default="kafka:29092", min_length=1)
    client_id: str = Field(default="school-service", min_length=1)
    acks: Literal["all"] = "all"
    topic: str = Field(default="school.events", min_length=1)
    request_timeout_ms: int = Field(default=10_000, ge=1_000)
    linger_ms: int = Field(default=5, ge=0)
    compression_type: Literal["gzip"] | None = "gzip"


class RedisSettings(BaseModel):
    user: str | None = None
    password: str | None = None
    host: str = Field(default="localhost", min_length=1)
    port: int = Field(default=6379, ge=1, le=65_535)
    database: int = Field(default=0, ge=0)
    default_ttl_seconds: int = Field(default=300, ge=1)
    scan_batch_size: int = Field(default=100, ge=1, le=10_000)
    key_prefix: str = Field(default="school-service", min_length=1)

    @property
    def url(self) -> str:
        credentials = ""
        if self.user is not None or self.password is not None:
            user = quote(self.user or "", safe="")
            password = quote(self.password or "", safe="")
            credentials = f"{user}:{password}@"

        return f"redis://{credentials}{self.host}:{self.port}/{self.database}"


class LoggingSettings(BaseModel):
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


class Settings(BaseSettings):
    db: DataBaseSettings
    api: ApiSettings
    middleware: MiddlewareSettings
    kafka: KafkaSettings = Field(default_factory=KafkaSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_CONFIG__",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
