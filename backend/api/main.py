"""FastAPI application entrypoint.

Run (from backend/):  uvicorn api.main:app --reload

The app is built by :func:`create_app` so production behaviour (docs disabled)
is unit-testable without import-time environment juggling. The module-level
``app`` is the instance uvicorn and the test suite import.
"""

import logging

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.routers import (
    admin,
    auth,
    forecasts,
    health,
    market,
    news,
    portfolios,
    stocks,
)
from core.config import Settings, get_settings
from core.rate_limit import limiter

logger = logging.getLogger(__name__)

# Baseline security headers applied to every response (W-6 / HIGH-003).
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}

# The interactive docs (non-prod only) load Swagger UI / ReDoc assets from the
# jsdelivr CDN, so the strict `default-src 'none'` would render a blank page.
# Relax the CSP for just those HTML routes; every other response keeps the
# locked-down baseline above.
_DOCS_CSP = (
    "default-src 'none'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "connect-src 'self'; "
    "img-src 'self' data: https://fastapi.tiangolo.com; "
    "font-src 'self' https://cdn.jsdelivr.net; "
    "worker-src 'self' blob:; "
    "frame-ancestors 'none'"
)
_DOCS_PATHS = frozenset({"/docs", "/redoc"})


def create_app(settings: Settings) -> FastAPI:
    """Build the application for the given settings.

    In production the interactive docs (``/docs``, ``/redoc``) and the schema
    (``/openapi.json``) are disabled so the full API surface is not disclosed to
    unauthenticated callers (Phase 5, ADR-0010).
    """
    is_prod = settings.environment == "production"

    app = FastAPI(
        title="AI Financial Intelligence Platform",
        version="0.1.0",
        description="Stock forecasting, news sentiment, and portfolio analytics.",
        docs_url=None if is_prod else "/docs",
        redoc_url=None if is_prod else "/redoc",
        openapi_url=None if is_prod else "/openapi.json",
    )

    # ---- rate limiting (per client IP) ----
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # ---- global exception sanitizer (MEDIUM-003 / W-12) ----
    @app.exception_handler(Exception)
    async def _sanitize_unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Log the real cause server-side; never leak traceback/SQL/paths to clients.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    @app.middleware("http")
    async def security_headers(request: Request, call_next) -> Response:
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        if request.url.path in _DOCS_PATHS:
            response.headers["Content-Security-Policy"] = _DOCS_CSP
        return response

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(stocks.router)
    app.include_router(forecasts.router)
    app.include_router(portfolios.router)
    app.include_router(news.router)
    app.include_router(market.router)
    app.include_router(admin.router)

    @app.get("/", tags=["root"])
    def root() -> dict[str, str]:
        info = {"service": "stock-prediction-backend"}
        if not is_prod:
            info["docs"] = "/docs"
        return info

    return app


settings = get_settings()
logging.basicConfig(level=settings.log_level)
app = create_app(settings)
