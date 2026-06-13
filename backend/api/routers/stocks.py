"""Stocks endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.schemas import StockDetailOut, StockOut
from db.session import get_db
from market_data.repository import StockRepository

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("", response_model=list[StockOut])
def list_stocks(db: Session = Depends(get_db)) -> list[StockOut]:
    repo = StockRepository(db)
    return [StockOut.model_validate(s) for s in repo.list_stocks()]


@router.get("/{symbol}", response_model=StockDetailOut)
def get_stock(symbol: str, db: Session = Depends(get_db)) -> StockDetailOut:
    repo = StockRepository(db)
    stock = repo.get_by_symbol(symbol)
    if stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Stock {symbol!r} not found"
        )
    detail = StockDetailOut.model_validate(stock)
    detail.price_count = repo.price_count(stock.id)
    return detail
