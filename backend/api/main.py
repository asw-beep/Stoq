"""FastAPI application entrypoint.

Run (from backend/):  uvicorn api.main:app --reload
"""

import logging

from fastapi import FastAPI, Request, Response

from api.routers import auth, forecasts, health, news, portfolios, stocks
from core.config import get_settings

settings = get_settings()
logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title="AI Financial Intelligence Platform",
    version="0.1.0",
    description="Stock forecasting, news sentiment, and portfolio analytics.",
)

# Baseline security headers applied to every response (W-6 / HIGH-003).
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}


@app.middleware("http")
async def security_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    for header, value in _SECURITY_HEADERS.items():
        response.headers.setdefault(header, value)
    return response


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(stocks.router)
app.include_router(forecasts.router)
app.include_router(portfolios.router)
app.include_router(news.router)


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {"service": "stock-prediction-backend", "docs": "/docs"}
