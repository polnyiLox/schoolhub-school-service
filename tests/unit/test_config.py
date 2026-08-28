import pytest
from pydantic import ValidationError

from app.core.config import DataBaseSettings, KafkaSettings, RedisSettings


def test_database_url_escapes_credentials_and_name() -> None:
    config = DataBaseSettings(
        user="school@admin",
        password="secret:/?#[]@!$&'()*+,;=",
        host="postgres",
        port=5432,
        name="school hub",
    )

    assert config.url == (
        "postgresql+asyncpg://school%40admin:"
        "secret%3A%2F%3F%23%5B%5D%40%21%24%26%27%28%29%2A%2B%2C%3B%3D"
        "@postgres:5432/school%20hub"
    )


@pytest.mark.parametrize(
    ("settings_type", "kwargs"),
    [
        (RedisSettings, {"port": 0}),
        (RedisSettings, {"default_ttl_seconds": 0}),
        (KafkaSettings, {"acks": 1}),
        (KafkaSettings, {"request_timeout_ms": 999}),
    ],
)
def test_invalid_external_service_settings_are_rejected(settings_type, kwargs) -> None:
    with pytest.raises(ValidationError):
        settings_type(**kwargs)
