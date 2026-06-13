"""Stock and historical price models."""

from __future__ import annotations

from datetime import date as date_type
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.forecast import Forecast


class Stock(Base, TimestampMixin):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    sector: Mapped[str | None] = mapped_column(String(120))

    prices: Mapped[list[HistoricalPrice]] = relationship(
        back_populates="stock", cascade="all, delete-orphan"
    )
    forecasts: Mapped[list[Forecast]] = relationship(
        back_populates="stock", cascade="all, delete-orphan"
    )


class HistoricalPrice(Base):
    __tablename__ = "historical_prices"
    __table_args__ = (UniqueConstraint("stock_id", "date", name="uq_price_stock_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), index=True, nullable=False
    )
    date: Mapped[date_type] = mapped_column(Date, nullable=False)
    open: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)

    stock: Mapped[Stock] = relationship(back_populates="prices")
