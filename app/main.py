import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import register_exception_handlers
from app.api.routers.v1 import router as v1_router
from app.broker import kafka_client, outbox_relay
from app.cache import redis_cache
from app.core.config import settings
from app.core.health import router as health_router
from app.core.logging import configure_logging
from app.db.session import engine_dispose

logger = logging.getLogger(__name__)


async def connect_cache() -> None:
    try:
        await redis_cache.connect()
    except Exception:
        logger.warning("Redis is unavailable; starting without cache")


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging(settings.logging.level)
    logger.info("Starting school-service")
    try:
        await connect_cache()
        await kafka_client.connect_producer()
        await outbox_relay.start()
        logger.info("School-service started")
        yield
    finally:
        logger.info("Stopping school-service")
        try:
            await outbox_relay.stop()
        finally:
            try:
                await kafka_client.close_producer()
            finally:
                try:
                    await redis_cache.close()
                finally:
                    await engine_dispose()
        logger.info("School-service stopped")


app = FastAPI(title="SchoolHub School Service", lifespan=lifespan)

app.include_router(health_router)
app.include_router(v1_router)
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.middleware.allow_origins,
    allow_methods=settings.middleware.allow_methods,
    allow_headers=settings.middleware.allow_headers,
    allow_credentials=settings.middleware.allow_credentials,
)
