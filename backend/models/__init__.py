"""ORM models package.

Importing any model triggers this package init, which imports every model module
so all mappers are registered before SQLAlchemy configures relationships. This
prevents "failed to locate a name" errors from string-based relationship targets.
"""

from models.forecast import Forecast
from models.news import NewsArticle, SentimentScore
from models.portfolio import Holding, Portfolio
from models.stock import HistoricalPrice, Stock
from models.user import User

__all__ = [
    "Forecast",
    "Holding",
    "HistoricalPrice",
    "NewsArticle",
    "Portfolio",
    "SentimentScore",
    "Stock",
    "User",
]
