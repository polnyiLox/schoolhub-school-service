import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.broker import kafka_client, outbox_relay
from app.cache import redis_cache
from app.db.session import engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


async def check_database() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database readiness check failed")
        return False
    return True


@router.get("/health")
@router.get("/health/live")
async def health_handler() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness_handler() -> JSONResponse:
    checks = {
        "database": "up" if await check_database() else "down",
        "kafka": "up" if kafka_client.is_connected else "down",
        "outbox_relay": "up" if outbox_relay.is_running else "down",
        "redis": "up" if redis_cache.is_connected else "degraded",
    }
    if any(checks[name] == "down" for name in ("database", "kafka", "outbox_relay")):
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "checks": checks},
        )
    return JSONResponse(content={"status": "ready", "checks": checks})
