"""API response/request schemas (Pydantic v2)."""

from __future__ import annotations

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


class HealthOut(BaseModel):
    # `environment` is deliberately NOT exposed — it discloses deployment posture
    # to unauthenticated callers (W-5 / HIGH-002).
    status: str
    database: str
