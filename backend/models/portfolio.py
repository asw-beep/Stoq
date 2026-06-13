"""Portfolio and holding models."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimestampMixin
from models.stock import Stock
from models.user import User


class Portfolio(Base, TimestampMixin):
    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    user: Mapped[User] = relationship(back_populates="portfolios")
    holdings: Mapped[list[Holding]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )


class Holding(Base, TimestampMixin):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), index=True, nullable=False
    )
    shares: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    purchase_price: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)

    portfolio: Mapped[Portfolio] = relationship(back_populates="holdings")
    stock: Mapped[Stock] = relationship()
