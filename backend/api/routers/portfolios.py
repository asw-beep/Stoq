"""Portfolio endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.pagination import Pagination, pagination_params
from api.schemas import (
    HoldingCreate,
    HoldingOut,
    Page,
    PortfolioAnalyticsOut,
    PortfolioCreate,
    PortfolioDetailOut,
    PortfolioSummaryOut,
)
from auth.dependencies import get_current_user
from db.session import get_db
from models.user import User
from portfolio.service import (
    HoldingNotFoundError,
    PortfolioNotFoundError,
    PortfolioService,
    UnknownStockError,
)

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


def get_service(db: Session = Depends(get_db)) -> PortfolioService:
    return PortfolioService(db)


@router.post("", response_model=PortfolioSummaryOut, status_code=status.HTTP_201_CREATED)
def create_portfolio(
    payload: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_service),
) -> PortfolioSummaryOut:
    portfolio = service.create(current_user.id, payload.name)
    return PortfolioSummaryOut(id=portfolio.id, name=portfolio.name, holding_count=0)


@router.get("", response_model=Page[PortfolioSummaryOut])
def list_portfolios(
    page: Pagination = Depends(pagination_params),
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_service),
) -> Page[PortfolioSummaryOut]:
    portfolios = service.list_for_user(
        current_user.id, limit=page.limit, offset=page.offset
    )
    items = [
        PortfolioSummaryOut(id=p.id, name=p.name, holding_count=len(p.holdings))
        for p in portfolios
    ]
    return Page(
        items=items,
        total=service.count_for_user(current_user.id),
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{portfolio_id}", response_model=PortfolioDetailOut)
def get_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_service),
) -> PortfolioDetailOut:
    try:
        val = service.get_valued(current_user.id, portfolio_id)
    except PortfolioNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        ) from None

    holdings_out = [
        HoldingOut(
            id=hv.holding.id,
            symbol=hv.holding.stock.symbol,
            shares=float(hv.holding.shares),
            purchase_price=float(hv.holding.purchase_price),
            current_price=hv.current_price,
            market_value=hv.market_value,
            cost_basis=hv.cost_basis,
            gain_loss=hv.gain_loss,
        )
        for hv in val.holdings
    ]
    return PortfolioDetailOut(
        id=val.portfolio.id,
        name=val.portfolio.name,
        holdings=holdings_out,
        total_cost=val.total_cost,
        total_value=val.total_value,
        total_gain_loss=val.total_gain_loss,
    )


@router.get("/{portfolio_id}/analytics", response_model=PortfolioAnalyticsOut)
def get_portfolio_analytics(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_service),
) -> PortfolioAnalyticsOut:
    try:
        result = service.get_analytics(current_user.id, portfolio_id)
    except PortfolioNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        ) from None
    return PortfolioAnalyticsOut(
        return_pct=result.return_pct,
        annualized_return=result.annualized_return,
        annualized_volatility=result.annualized_volatility,
        sharpe_ratio=result.sharpe_ratio,
        max_drawdown=result.max_drawdown,
    )


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_service),
) -> None:
    try:
        service.delete(current_user.id, portfolio_id)
    except PortfolioNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        ) from None


@router.post(
    "/{portfolio_id}/holdings",
    response_model=HoldingOut,
    status_code=status.HTTP_201_CREATED,
)
def add_holding(
    portfolio_id: int,
    payload: HoldingCreate,
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_service),
) -> HoldingOut:
    try:
        holding = service.add_holding(
            current_user.id,
            portfolio_id,
            payload.symbol,
            payload.shares,
            payload.purchase_price,
        )
    except PortfolioNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        ) from None
    except UnknownStockError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from None
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from None

    repo = service.repo
    current_price = repo.latest_close(holding.stock_id)
    shares = float(holding.shares)
    purchase_price = float(holding.purchase_price)
    cost_basis = shares * purchase_price
    market_value = shares * current_price if current_price is not None else None
    gain_loss = (market_value - cost_basis) if market_value is not None else None

    return HoldingOut(
        id=holding.id,
        symbol=holding.stock.symbol,
        shares=shares,
        purchase_price=purchase_price,
        current_price=current_price,
        market_value=market_value,
        cost_basis=cost_basis,
        gain_loss=gain_loss,
    )


@router.delete(
    "/{portfolio_id}/holdings/{holding_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_holding(
    portfolio_id: int,
    holding_id: int,
    current_user: User = Depends(get_current_user),
    service: PortfolioService = Depends(get_service),
) -> None:
    try:
        service.remove_holding(current_user.id, portfolio_id, holding_id)
    except PortfolioNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        ) from None
    except HoldingNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Holding not found"
        ) from None
