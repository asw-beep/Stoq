"""FastAPI application entrypoint.

Run (from backend/):  uvicorn api.main:app --reload
"""

import logging

from fastapi import FastAPI

from api.routers import health, stocks
from core.config import get_settings

settings = get_settings()
logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title="AI Financial Intelligence Platform",
    version="0.1.0",
    description="Stock forecasting, news sentiment, and portfolio analytics.",
)

app.include_router(health.router)
app.include_router(stocks.router)


@app.get("/", tags=["root"])
def root() -> dict[str, str]:
    return {"service": "stock-prediction-backend", "docs": "/docs"}
