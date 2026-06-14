"""Forecast model (model output per stock and target date)."""

from __future__ import annotations

from datetime import date as date_type

from sqlalchemy import Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimestampMixin
from models.stock import Stock


class Forecast(Base, TimestampMixin):
    __tablename__ = "forecasts"
    # One prediction per (stock, model, run-date, target-date): re-running a model
    # on the same day replaces that day's rows rather than duplicating them.
    __table_args__ = (
        UniqueConstraint(
            "stock_id",
            "model",
            "forecast_date",
            "target_date",
            name="uq_forecast_stock_model_dates",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Date the forecast was generated, and the date it predicts for.
    forecast_date: Mapped[date_type] = mapped_column(Date, nullable=False)
    target_date: Mapped[date_type] = mapped_column(Date, nullable=False)
    model: Mapped[str] = mapped_column(String(40), nullable=False)  # e.g. prophet, xgboost
    predicted_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric(6, 4))

    stock: Mapped[Stock] = relationship(back_populates="forecasts")
