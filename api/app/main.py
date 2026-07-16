"""BOM Guardian AI — FastAPI application.

Structured errors (no stack traces to clients), correlation IDs on every
request, restricted CORS, versioned routes under /api/v1.
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.app.routers import analytics, bom, copilot, health, issues, parts, scenarios
from bom_guardian import __version__
from bom_guardian.config import get_settings
from bom_guardian.observability import configure_logging, get_logger

configure_logging()
log = get_logger("api")

app = FastAPI(
    title="BOM Guardian AI",
    version=__version__,
    description="Supply chain data quality and BOM remediation platform API",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    correlation_id = request.headers.get("X-Correlation-ID", f"REQ-{uuid.uuid4().hex[:12]}")
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", None)
    log.error("unhandled_error", path=str(request.url.path), error=str(exc)[:500])
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": "An unexpected error occurred.",  # no stack traces to clients
            "correlation_id": correlation_id,
        },
    )


for router in (
    health.router,
    parts.router,
    issues.router,
    bom.router,
    scenarios.router,
    analytics.router,
    copilot.router,
):
    app.include_router(router, prefix="/api/v1")
