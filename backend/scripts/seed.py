"""Bootstrap script: ingest seed symbols and their price history.

Usage (from backend/, with the venv active and DB migrated):
    python -m scripts.seed
    python -m scripts.seed AAPL MSFT        # override symbols
"""

from __future__ import annotations

import logging
import sys

from core.config import get_settings
from db.session import SessionLocal
from market_data.provider import get_provider
from market_data.service import MarketDataService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("seed")


def main(argv: list[str]) -> int:
    settings = get_settings()
    symbols = [s.upper() for s in argv] if argv else settings.seed_symbol_list
    logger.info("Seeding %d symbols: %s", len(symbols), ", ".join(symbols))

    provider = get_provider(settings.market_data_provider)
    db = SessionLocal()
    try:
        service = MarketDataService(db, provider)
        results = service.ingest_many(symbols, settings.history_years)
    finally:
        db.close()

    for r in results:
        logger.info("%-8s %6d new bars, %6d total", r.symbol, r.bars_ingested, r.total_bars)
    logger.info("Done: %d/%d symbols ingested", len(results), len(symbols))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
