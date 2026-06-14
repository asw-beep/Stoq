# Backend — AI Financial Intelligence Platform

FastAPI modular monolith. See `../docs/Architecutre.md` for the big picture.

## Layout

```
backend/
├── core/          # config (pydantic-settings), security (bcrypt + JWT), validation
├── db/            # SQLAlchemy Base, engine, session
├── models/        # ORM models (users, stocks, prices, forecasts, news, portfolios)
├── auth/          # JWT auth: repository + service + access-control dependencies
├── market_data/   # yfinance ETL: provider + repository + service
├── api/           # FastAPI app, schemas, routers (health, auth, stocks)
├── scripts/       # seed.py (bootstrap symbols + history)
├── alembic/       # migrations
└── tests/         # pytest (SQLite, no external services)
```

## Local setup (host)

```bash
cd backend
uv sync --extra dev            # create venv + install deps
# start the DB (from repo root):  docker compose up -d db
uv run alembic upgrade head    # create schema
uv run python -m scripts.seed  # ingest AAPL, MSFT, ... (5y daily)
uv run uvicorn api.main:app --reload
```

API docs: http://localhost:8000/docs

## Full stack (Docker)

```bash
# from repo root
docker compose up --build      # db + backend (migrations run on start)
```

## Tests

```bash
cd backend
uv run pytest
```

## Migrations

```bash
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```
