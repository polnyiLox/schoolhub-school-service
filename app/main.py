from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.health import router as health_router
from app.db.session import engine_dispose
from app.exceptions import AccessDeniedError, AppError, ConflictError, NotFoundError, ValidationError
from app.api.routers.v1 import router as v1_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await engine_dispose()


app = FastAPI(title="SchoolHub School Service", lifespan=lifespan)

app.include_router(health_router)
app.include_router(v1_router, prefix=settings.api.v1_prefix)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.middleware.allow_origins,
    allow_methods=settings.middleware.allow_methods,
    allow_headers=settings.middleware.allow_headers,
    allow_credentials=settings.middleware.allow_credentials
)


@app.exception_handler(AppError)
async def app_errors_handler(_: Request, exc: AppError) -> JSONResponse:
    if isinstance(exc, NotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, AccessDeniedError):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, ConflictError):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, ValidationError):
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.detail},
    )
