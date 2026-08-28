from functools import lru_cache
from typing import Literal
from urllib.parse import quote

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DataBaseSettings(BaseModel):
    user: str
    password: str
    host: str
    port: int
    name: str

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class ApiSettings(BaseModel):
    v1_prefix: str
    host: str
    port: int
    reload: bool


class MIddlewareSettings(BaseModel):
    allow_origins: list[str]
    allow_methods: list[str]
    allow_headers: list[str]
    allow_credentials: bool


class KafkaSettings(BaseModel):
    bootstrap_servers: str = "kafka:29092"
    client_id: str = "school-service"
    acks: Literal[0, 1, "all"] = "all"
    topic: str = "school.events"
    request_timeout_ms: int = 10_000


class RedisSettings(BaseModel):
    user: str | None = None
    password: str | None = None
    host: str = "localhost"
    port: int = 6379
    database: int = 0
    default_ttl_seconds: int = 300
    key_prefix: str = "school-service"

    @property
    def url(self) -> str:
        credentials = ""
        if self.user is not None or self.password is not None:
            user = quote(self.user or "", safe="")
            password = quote(self.password or "", safe="")
            credentials = f"{user}:{password}@"

        return f"redis://{credentials}{self.host}:{self.port}/{self.database}"


class Settings(BaseSettings):
    db: DataBaseSettings
    api: ApiSettings
    middleware: MIddlewareSettings
    kafka: KafkaSettings = Field(default_factory=KafkaSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_CONFIG__",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
