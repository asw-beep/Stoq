"""Stocks endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.schemas import StockDetailOut, StockOut
from core.validation import normalize_symbol
from db.session import get_db
from market_data.repository import StockRepository

router = APIRouter(prefix="/stocks", tags=["stocks"])


def valid_symbol(symbol: str) -> str:
    """Path-param dependency: normalize + validate, returning HTTP 422 on bad input.

    Rejects malformed symbols at the edge before any DB/provider work (W-3).
    """
    try:
        return normalize_symbol(symbol)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid stock symbol",
        ) from None


@router.get("", response_model=list[StockOut])
def list_stocks(db: Session = Depends(get_db)) -> list[StockOut]:
    repo = StockRepository(db)
    return [StockOut.model_validate(s) for s in repo.list_stocks()]


@router.get("/{symbol}", response_model=StockDetailOut)
def get_stock(
    symbol: str = Depends(valid_symbol), db: Session = Depends(get_db)
) -> StockDetailOut:
    repo = StockRepository(db)
    stock = repo.get_by_symbol(symbol)
    if stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Stock {symbol!r} not found"
        )
    detail = StockDetailOut.model_validate(stock)
    detail.price_count = repo.price_count(stock.id)
    return detail
