import time

from fastapi import APIRouter, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

HTTP_REQUESTS = Counter(
    "schoolhub_http_requests_total",
    "Total HTTP requests",
    ("service", "method", "route", "status"),
)
HTTP_DURATION = Histogram(
    "schoolhub_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ("service", "method", "route"),
)
OUTBOX_PUBLISHES = Counter(
    "schoolhub_outbox_publishes_total", "Outbox publish results", ("result",)
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        route = getattr(request.scope.get("route"), "path", "unmatched")
        labels = ("school-service", request.method, route)
        HTTP_REQUESTS.labels(*labels, str(response.status_code)).inc()
        HTTP_DURATION.labels(*labels).observe(time.perf_counter() - started)
        return response


router = APIRouter()


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
