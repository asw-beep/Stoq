# API Specification (implemented)

All data endpoints require a Bearer JWT (`Authorization: Bearer <token>`).
List endpoints return a pagination envelope `{items, total, limit, offset}`.

## Auth

```
POST /auth/register     # {email, password} -> 201 {id, email, role}        (3/min)
POST /auth/login        # OAuth2 form (username=email, password) -> {access_token, token_type}  (5/min)
GET  /auth/me           # current user
```

## Stocks & prices

```
GET /stocks                      # Page[StockOut]  ?limit(1-200)=50 &offset=0
GET /stocks/{symbol}             # StockDetailOut (metadata + price_count); symbol ^[A-Z0-9.-]{1,20}$
GET /stocks/{symbol}/prices      # list[PriceBarOut] oldest-first; ?range=1m|3m|6m|1y|max (default 1y)
```

## Forecasts (nested under a stock)

```
GET  /stocks/{symbol}/forecasts          # list[ForecastOut]; optional ?model=
POST /stocks/{symbol}/forecasts          # {horizons:[1,7,30]} ?model=prophet|xgboost -> 201  (5/min)
```

## News & sentiment (nested under a stock)

```
GET  /stocks/{symbol}/news       # list[NewsArticleOut] (each with per-article sentiment); ?limit(1-200)=50
POST /stocks/{symbol}/news       # ingest+score from Finnhub; ?days(1-90)=7 -> 201  (5/min; needs FINNHUB_API_KEY)
```

## Portfolios

```
GET    /portfolios                              # Page[PortfolioSummaryOut]
POST   /portfolios                              # {name} -> 201
GET    /portfolios/{id}                         # PortfolioDetailOut (holdings + valuations)
GET    /portfolios/{id}/analytics               # PortfolioAnalyticsOut: return_pct, annualized_return/volatility, sharpe_ratio, max_drawdown
DELETE /portfolios/{id}                         # 204
POST   /portfolios/{id}/holdings                # {symbol, shares, purchase_price} -> 201
DELETE /portfolios/{id}/holdings/{holding_id}   # 204
```

## Market

```
GET /market/overview     # list[MarketOverviewItem]: latest_close, previous_close, change, change_pct per stock
GET /market/signals      # list[MarketSignalItem]: latest directional signal (direction, probability, dates) per stock with a forecast
GET /market/sentiment    # list[MarketSentimentItem]: positive/negative/neutral/total sentiment counts per stock (zeros if no news)
```

## Ops

```
GET /health              # {status, database}  (no auth; no environment disclosure)
```

Notes:
- Global rate limit: 60/min per IP; stricter per-route limits noted above.
- `/docs`, `/redoc`, `/openapi.json` are disabled when `ENVIRONMENT=production`.
