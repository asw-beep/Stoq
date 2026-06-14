"""Forecast endpoints (nested under /stocks/{symbol}).

Reuses the Phase 1.5 symbol-validation contract (``valid_symbol`` declared
before auth so malformed input 422s even unauthenticated) and the Phase 1.6
auth dependency, exactly like the stocks router.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.routers.stocks import valid_symbol
from api.schemas import ForecastOut, ForecastRequest
from auth.dependencies import get_current_user
from db.session import get_db
from forecasting.models.base import Forecaster
from forecasting.models.factory import SUPPORTED_MODELS, build_forecaster
from forecasting.service import ForecastingService, UnknownStockError
from models.user import User

router = APIRouter(prefix="/stocks/{symbol}/forecasts", tags=["forecasts"])


def get_forecaster(model: str = "prophet") -> Forecaster:
    """Resolve the requested forecasting model (overridable in tests via DI).

    ``model`` is a query param; unknown names 422 rather than 500.
    """
    try:
        return build_forecaster(model)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown forecasting model; supported: {', '.join(SUPPORTED_MODELS)}",
        ) from None


@router.post("", response_model=list[ForecastOut], status_code=status.HTTP_201_CREATED)
def create_forecast(
    payload: ForecastRequest,
    symbol: str = Depends(valid_symbol),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    forecaster: Forecaster = Depends(get_forecaster),
) -> list[ForecastOut]:
    """Generate and persist forecasts for a stock (synchronous; ADR-0009)."""
    horizons = payload.normalized_horizons()
    if not horizons:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one positive horizon is required",
        )
    service = ForecastingService(db, forecaster)
    try:
        result = service.generate(symbol, horizons)
    except UnknownStockError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from None
    except ValueError as exc:
        # Not enough history / bad input for the model.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from None
    return [ForecastOut.model_validate(f) for f in result.forecasts]


@router.get("", response_model=list[ForecastOut])
def get_forecasts(
    symbol: str = Depends(valid_symbol),
    model: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ForecastOut]:
    """Read the most recent stored forecasts for a stock (optionally one model)."""
    # Reads only — no model construction needed; ``model`` filters by stored name.
    service = ForecastingService(db)
    try:
        rows = service.latest(symbol, model)
    except UnknownStockError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from None
    return [ForecastOut.model_validate(f) for f in rows]
