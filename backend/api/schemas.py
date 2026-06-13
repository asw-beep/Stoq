"""API response/request schemas (Pydantic v2)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    name: str | None = None
    sector: str | None = None


class StockDetailOut(StockOut):
    price_count: int = 0


class HealthOut(BaseModel):
    status: str
    environment: str
    database: str
