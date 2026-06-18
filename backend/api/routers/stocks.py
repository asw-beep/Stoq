"""Stocks endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.pagination import Pagination, pagination_params
from api.schemas import Page, StockDetailOut, StockOut
from auth.dependencies import get_current_user
from core.validation import normalize_symbol
from db.session import get_db
from market_data.repository import StockRepository
from models.user import User

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


@router.get("", response_model=Page[StockOut])
def list_stocks(
    page: Pagination = Depends(pagination_params),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Page[StockOut]:
    repo = StockRepository(db)
    items = [
        StockOut.model_validate(s)
        for s in repo.list_stocks(limit=page.limit, offset=page.offset)
    ]
    return Page(
        items=items,
        total=repo.count_stocks(),
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{symbol}", response_model=StockDetailOut)
def get_stock(
    # `valid_symbol` is declared first so a bad symbol is rejected with 422
    # before the auth check runs (an unauthenticated bad request still 422s).
    symbol: str = Depends(valid_symbol),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
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
