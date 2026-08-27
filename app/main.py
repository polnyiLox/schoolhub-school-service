from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import register_exception_handlers
from app.api.routers.v1 import router as v1_router
from app.core.config import settings
from app.core.health import router as health_router
from app.db.session import engine_dispose


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await engine_dispose()


app = FastAPI(title="SchoolHub School Service", lifespan=lifespan)

app.include_router(health_router)
app.include_router(v1_router)
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.middleware.allow_origins,
    allow_methods=settings.middleware.allow_methods,
    allow_headers=settings.middleware.allow_headers,
    allow_credentials=settings.middleware.allow_credentials
)
