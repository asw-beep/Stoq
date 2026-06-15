"""API response/request schemas (Pydantic v2)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    # bcrypt operates on the first 72 bytes; cap length to avoid silent truncation.
    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class StockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    name: str | None = None
    sector: str | None = None


class StockDetailOut(StockOut):
    price_count: int = 0


class ForecastRequest(BaseModel):
    # Day offsets to predict (default 1/7/30 per ML_Design). Bounded to keep
    # training cheap and the request synchronous (ADR-0009).
    horizons: list[int] = Field(default=[1, 7, 30], min_length=1, max_length=10)

    def normalized_horizons(self) -> list[int]:
        # De-duplicate, drop non-positive, sort — Prophet predicts up to max(h).
        return sorted({h for h in self.horizons if h > 0})


class ForecastOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    forecast_date: date
    target_date: date
    model: str
    predicted_price: float
    confidence: float | None = None


# ---- portfolio ----

class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class HoldingCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    shares: float = Field(gt=0)
    purchase_price: float = Field(gt=0)


class HoldingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    shares: float
    purchase_price: float
    current_price: float | None = None
    market_value: float | None = None
    cost_basis: float
    gain_loss: float | None = None


class PortfolioSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    holding_count: int = 0


class PortfolioDetailOut(BaseModel):
    id: int
    name: str
    holdings: list[HoldingOut] = []
    total_cost: float = 0.0
    total_value: float | None = None
    total_gain_loss: float | None = None


class HealthOut(BaseModel):
    # `environment` is deliberately NOT exposed — it discloses deployment posture
    # to unauthenticated callers (W-5 / HIGH-002).
    status: str
    database: str
