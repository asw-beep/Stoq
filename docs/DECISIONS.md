# Architecture Decision Log

Every major architectural decision is recorded here, as required by `docs/CLAUDE.md`.
Format: each entry has a date, context, decision, and consequences.

---

## ADR-0001 — Cloud provider: GCP (was AWS)

**Date:** 2026-06-13
**Status:** Accepted

**Context:** Original docs targeted AWS EC2 for deployment. User requested switching
to GCP wherever applicable.

**Decision:** Deploy on **GCP Compute Engine** (single VM running Docker Compose),
mirroring the original EC2 + Compose design. Adopt a **hybrid** strategy: ship on
Compute Engine now, document a future migration to Cloud Run + Cloud SQL +
Artifact Registry (recorded in `docs/Devops.md`).

**Consequences:**
- Deployment target renamed across `Devops.md`, `Tech_stack.md`, `Tasks.md`, `Roadmap.md`.
- Monitoring stays vendor-neutral (self-hosted Prometheus + Grafana), so the stack
  remains portable if we later move clouds.
- No application code changes required by this decision.

---

## ADR-0002 — Authentication: JWT login/register with users table

**Date:** 2026-06-13
**Status:** Accepted

**Context:** `Database.md` had a `portfolios` table but no owner. The project is an
AI-engineer portfolio piece, and the requirements template already included
`SECRET_KEY` / `ACCESS_TOKEN_EXPIRE_MINUTES`.

**Decision:** Add a `users` table and JWT-based auth (register + login), bcrypt
password hashing. Portfolios are owned by users (`portfolios.user_id`). Roles are
deferred (single implicit `user` role for now, schema leaves room for `admin`).

**Consequences:**
- New `users` table; `portfolios` gains `user_id` FK (recorded in `Database.md`).
- Auth endpoints are implemented in the Backend APIs phase; the schema/models land
  in Phase 1 so the initial migration is complete.

---

## ADR-0003 — Local PostgreSQL runs in Docker

**Date:** 2026-06-13
**Status:** Accepted

**Context:** The project folder shipped with a bundled PostgreSQL 18.4 install. We
needed a consistent, reproducible local database.

**Decision:** Run PostgreSQL as a **Docker container** via Docker Compose. The bundled
`PostgreSQL/` directory is gitignored and unused (kept only as an offline fallback).

**Consequences:**
- No host-level Postgres install required.
- DB config lives in `docker-compose.yml`; data persists in a named Docker volume.

---

## ADR-0004 — Dedicated git repository

**Date:** 2026-06-13
**Status:** Accepted

**Context:** The project lived inside an umbrella repo at `E:/Projects` containing many
unrelated projects.

**Decision:** Initialize a **dedicated git repository** at the project root so it can be
pushed to GitHub independently and drive its own CI/CD.

**Consequences:**
- Project root is the repo root; all tooling (Compose, Actions) assumes this.

---

## ADR-0005 — Python dependency & env management with uv

**Date:** 2026-06-13
**Status:** Accepted

**Context:** Tech stack did not specify a Python package manager. `uv` is already
installed on the dev machine.

**Decision:** Use **uv** with a `pyproject.toml` for dependency management and virtual
environments (instead of Poetry/pip-tools).

**Consequences:**
- Faster installs; single `pyproject.toml` source of truth.
- Heavy ML deps (Prophet, XGBoost, Transformers) are added in their respective phases
  to keep the Phase 1 environment light.

---

## ADR-0006 — Phase 1.5 security hardening & symbol-validation test reconciliation

**Date:** 2026-06-14
**Status:** Accepted

**Context:** Phase 1.5 implemented the six security controls gated by the
strict-xfail tests in `backend/tests/test_security.py`. While turning the
symbol-validation gate (CRITICAL-002) green, two tests proved unsatisfiable as
written, because the HTTP test client mangles certain inputs before they reach
the app:

- `test_reflected_symbol_is_json_encoded` sent `/stocks/<script>` and asserted a
  **404**. Once `^[A-Z0-9.-]{1,20}$` validation lands, `<script>` is correctly
  rejected with **422**, so the original assertion can never hold.
- Two `BAD_INPUT_PAYLOADS` entries (`../../etc/passwd`, `<script>alert(1)</script>`)
  contain `/`; the client splits/normalizes them into a different path that never
  hits the `/stocks/{symbol}` route, so they return 404, not 422.

**Decision:**
- Validation is enforced in **two layers** sharing one rule (`core/validation.py`,
  `normalize_symbol`): a FastAPI path-param dependency (HTTP 422) and the
  `MarketDataService` (raises `ValueError` *before* any outbound provider call).
- Reconcile the tests to the implemented contract rather than weaken the control:
  - Split the reflection test — a valid-but-missing symbol (`ZZZZ`) exercises the
    JSON-encoded **404** path; a new `test_invalid_symbol_error_is_json_encoded`
    asserts the **422** rejection body is JSON. Both preserve the original intent
    (rejected input never reaches an unescaped context).
  - Restrict `BAD_INPUT_PAYLOADS` to **single-segment** inputs the client delivers
    intact. The `/`-containing path-traversal payloads are covered at the service
    layer (`test_service_rejects_bad_symbol_before_provider_call`), matching the
    suite's existing defense-in-depth note about client-mangled control chars.

**Consequences:**
- All six Phase 1.5 controls are implemented and their strict-xfail markers
  removed; suite is `29 passed, 3 xfailed` (the 3 remaining xfails are the
  Phase 1.6 auth/password gates).
- The weak-secret check (`core/config.py`) rejects placeholder markers
  (`change-me`, `use-openssl`) and secrets shorter than 32 chars **only** when
  `ENVIRONMENT=production`, so local development is unaffected.

---

## ADR-0007 — Password hashing: bcrypt directly (passlib dropped)

**Date:** 2026-06-14
**Status:** Accepted (supersedes the passlib choice implied by ADR-0002)

**Context:** Phase 1.6 implemented the password-hashing service. The originally
listed `passlib[bcrypt]` (Tasks.md) fails at import against modern `bcrypt`
(>= 4.1): passlib 1.7.4's backend-detection probe passes a >72-byte test string
to `bcrypt.hashpw`, which now raises `ValueError` instead of truncating, breaking
the bcrypt backend entirely. passlib has been unmaintained since 2020.

**Decision:** Use the maintained **`bcrypt`** package directly in
`core/security.py` (`hash_password` / `verify_password`), instead of wrapping it
in passlib. Inputs are explicitly truncated to bcrypt's 72-byte limit so hashing
and verification apply the same rule and long inputs never raise.

**Consequences:**
- Drops the unmaintained `passlib` dependency; no version-pinning workaround.
- `core/security.py` also holds the JWT primitives (`create_access_token`,
  `decode_access_token`) using `python-jose`, so all crypto lives in one module.
- Auth stack additions: `python-multipart` (OAuth2 password form) and
  `email-validator` (pydantic `EmailStr`).

---

## ADR-0008 — Auth model: OAuth2 bearer JWT, centralized access-control dependencies

**Date:** 2026-06-14
**Status:** Accepted

**Context:** Phase 1.6 needed authentication on data endpoints plus an
authorization scheme that later user-scoped phases (portfolios) can reuse without
re-implementing checks (the W-1 IDOR risk).

**Decision:**
- **Authentication:** OAuth2 password flow issuing a signed JWT (`sub` = user id,
  `iat`/`exp` claims). `POST /auth/register`, `POST /auth/login`, `GET /auth/me`.
  Login verifies a dummy hash for unknown emails to keep timing uniform
  (no user enumeration).
- **Authorization choke points** in `auth/dependencies.py`: `get_current_user`
  (401 on missing/invalid token), `require_role(*roles)` (403), and
  `require_portfolio_owner()` — returns **404** for both missing and
  not-owned portfolios so existence is not disclosed. Built now, ahead of the
  portfolio endpoints, so ownership is enforced from day one (Phase 4).
- `/stocks` endpoints are protected; on the detail route `valid_symbol` is
  declared **before** `get_current_user` so a malformed symbol returns 422 even
  when unauthenticated (preserves the Phase 1.5 validation contract).

**Consequences:**
- `test_endpoints_require_auth` and `test_password_service_hashes_and_verifies`
  flip green; `backend/tests/test_security.py` now has **no** xfail markers left.
- Existing `/stocks` tests authenticate via new `make_user` / `auth_headers`
  conftest fixtures. Full suite: `45 passed`.
- No schema change — `users`/`portfolios` already shipped in the Phase 1 initial
  migration (ADR-0002), so no new Alembic revision was required.

---

## ADR-0009 — Forecasting engine: synchronous generation, Protocol-based models

**Date:** 2026-06-14
**Status:** Accepted

**Context:** Phase 2 introduces the forecasting engine (Prophet first, XGBoost
next). Two cross-cutting choices needed recording: how training executes relative
to the request, and how multiple models coexist without the service knowing about
each one.

**Decision:**
- **Synchronous generation.** `POST /stocks/{symbol}/forecasts` trains and
  predicts inline, persists, and returns the forecasts (HTTP 201). Background/
  async execution (a task queue or `BackgroundTasks` + polling) is a deliberate
  deferral — it is only worth its added status-tracking complexity at a scale we
  don't have, and Phase 5 rate limiting covers the worker-exhaustion risk. The
  request horizon count is bounded (≤10) to keep training cheap.
- **`Forecaster` Protocol** (`forecasting/models/base.py`) mirrors
  `MarketDataProvider`: `ProphetForecaster` implements it now, `XGBoostForecaster`
  later, and `ForecastingService` depends only on the abstraction (injected via a
  `get_forecaster` FastAPI dependency, which tests override with a stub — no heavy
  training in unit tests). Heavy libs (`prophet`, `xgboost`) are **lazy-imported**
  inside the model methods, matching `YFinanceProvider`, so the package imports
  and the suite runs without those wheels installed.
- **New module `forecasting/`** follows the `market_data/` layout: pure
  `features.py` (SMA/EMA/RSI/MACD/volatility) and `evaluation.py` (RMSE/MAE/MAPE),
  a `ForecastRepository`, and a `ForecastingService`. The symbol is validated via
  `normalize_symbol` before any work (Phase 1.5 contract); endpoints sit under
  `/stocks/{symbol}` and reuse `valid_symbol` + `get_current_user` (Phase 1.6).
- **Persistence grain.** A `uq_forecast_stock_model_dates` unique constraint
  (`stock_id, model, forecast_date, target_date`) is added via Alembic revision
  `b1f2c3d4e5a6`. The repository persists with a **dialect-agnostic
  delete-then-insert** (not `pg_insert`) so a re-run for the same day replaces
  that day's rows and the same code runs on Postgres (prod) and SQLite (tests).

**Consequences:**
- `models/forecast.py` gains the unique constraint; one new migration, no data
  migration (table is empty).
- Full suite: `68 passed` (was 45); ruff clean. New tests cover features,
  metrics, the service (stub forecaster), and the API (auth/validation/happy path).
- XGBoost landed as a second `Forecaster` implementation
  (`forecasting/models/xgboost_model.py`), reusing `features.py`, the repository,
  service, and endpoints unchanged — validating the abstraction. It uses a
  **direct multi-step** strategy (one regressor trained per horizon to map
  today's features to the close price `h` days ahead) and reports
  `confidence=None` (gradient-boosted regression has no native prediction
  interval, unlike Prophet's `yhat` bounds).

---

## ADR-0010 — Phase 5 API hardening: pagination, rate limiting, docs gating, error sanitizing

**Date:** 2026-06-18
**Status:** Accepted

**Context:** Phase 5 is the API-hardening phase and a prerequisite for the CI
security gate (Phase 8) and the authenticated DAST/ZAP scan (Phase 12), which is
only meaningful once these controls exist (`docs/Roadmap.md`). Four controls were
required: pagination on list endpoints, rate limiting, a global exception
sanitizer, and disabling interactive docs in production.

**Decision:**

- **Pagination — `{items, total, limit, offset}` envelope.** A generic
  `Page[T]` schema (`api/schemas.py`, PEP 695 generic) plus a single
  `pagination_params` dependency (`api/pagination.py`, `limit` 1–200 default 50,
  `offset` ≥ 0; out-of-range → 422). `GET /stocks` and `GET /portfolios` return
  the envelope; repositories gained `limit`/`offset` + `count_*` methods. The
  envelope (over a bare bounded list) gives the Phase 6 frontend a `total` for
  page counts; this is an intentional response-shape change to endpoints with no
  external consumers yet. `GET /stocks/{symbol}/news` already had a bounded
  `limit` and is unchanged.
- **Rate limiting — `slowapi`, per client IP, strict.** A module-level
  `limiter` (`core/rate_limit.py`, separate module so routers import it without a
  cycle through `api.main`). Registered on the app with `SlowAPIMiddleware` (a
  permissive `60/minute` global default) plus stricter per-route decorators:
  login `5/min`, register `3/min`, forecast-generate and news-ingest `5/min`
  (the expensive/abuse-prone POSTs). The login limit is the primary control —
  brute-force protection. Disabled suite-wide in `conftest` (`limiter.enabled =
  False`) so existing looping tests don't trip; `test_rate_limit.py` re-enables
  it locally.
- **Docs disabled in production via an app factory.** App construction moved into
  `create_app(settings) -> FastAPI`; the module-level `app = create_app(...)` is
  unchanged for uvicorn/tests. When `environment == "production"`, `docs_url`,
  `redoc_url`, and `openapi_url` are `None` so the full API surface is not
  disclosed to unauthenticated callers. The factory makes this unit-testable
  without import-time env juggling (`test_main.py`).
- **Global exception sanitizer.** `@app.exception_handler(Exception)` logs the
  real cause server-side and returns a generic `500 {"detail": "Internal server
  error"}` — no traceback / ORM / path leakage. Extends the W-12 guarantee
  (`test_error_body_has_no_internal_traces`) from the 404 path to genuine 500s.

**Consequences:**

- New deps: `slowapi>=0.1.9` (pulls `limits`, `deprecated`, `wrapt`); added to
  `pyproject.toml` and `uv.lock`.
- New modules: `api/pagination.py`, `core/rate_limit.py`. New tests:
  `test_rate_limit.py`, `test_main.py`; list-endpoint tests updated to the
  envelope shape. Full suite: **119 passed** (was 72); the security suite is
  unchanged and still green.
- The `secret_key` field on `Settings` is now also exercised in production mode
  by `test_main.py` (uses a strong 40-char secret to pass the W-2 check).
- Pre-existing lint debt surfaced separately: the installed `ruff` is 0.15.17
  (pin is `>=0.7`), which flags `B904`/`UP`/`I001` issues in untouched Phase 3/4
  files. Out of scope here; to be addressed when Phase 8 pins a ruff version for
  the CI gate. Phase 5 code itself is ruff-clean.
- Model selection moved behind a `build_forecaster(name)` factory
  (`forecasting/models/factory.py`, mirroring `market_data.get_provider`); the
  API picks the model via a `?model=` query param (default `prophet`, unknown →
  422). `ForecastingService.forecaster` is now optional because the read path
  (`latest`) needs no model. Suite after XGBoost: `72 passed, 1 skipped` (the
  skip is the live-training test, gated on the `xgboost` wheel via
  `importorskip`); ruff clean.

---

## ADR-0011 — Phase 5.5 read endpoints + Phase 6 frontend architecture

**Date:** 2026-06-18
**Status:** Accepted

**Context:** Phase 6 is the Next.js dashboard (PRD F4). Two read-only gaps blocked
a useful UI: no historical-price series endpoint (only `price_count`) and no
market-overview aggregate. The frontend also needs an auth + cross-origin story.

**Decision:**

- **Phase 5.5 additive read endpoints** (no breaking changes): `GET
  /stocks/{symbol}/prices?range=1m|3m|6m|1y|max` returns OHLC bars oldest-first
  (`PriceBarOut`), and `GET /market/overview` returns latest close + day-over-day
  change per tracked stock (`MarketOverviewItem`). Both reuse the existing
  Repository → Router layering, `valid_symbol`, and `get_current_user`. Advanced
  risk metrics (Sharpe/volatility/drawdown) are **deferred** — not needed for the
  first dashboard.
- **Frontend = Next.js BFF.** The browser never holds the JWT. Next.js route
  handlers (`src/app/api/*`) proxy to FastAPI: `/api/auth/login` exchanges
  credentials and sets an **httpOnly, secure, sameSite=lax** cookie; a catch-all
  `/api/[...path]` attaches `Authorization: Bearer` from that cookie and forwards.
  Consequence: **no CORS** on the backend (calls are server-to-server) and the
  token is **not exposed to JS** (XSS-safe). `middleware.ts` guards app routes.
- **Light-first theme**, **TanStack Query** for client data/caching/mutations,
  **react-hook-form + zod** for forms, **Recharts** for price/forecast/sentiment/
  allocation charts — per `docs/Tech_stack.md`.

**Consequences:**

- New backend: `api/routers/market.py`, `PriceBarOut`/`MarketOverviewItem`
  schemas, `StockRepository.list_prices` + `latest_two_closes`. Suite: **129
  passed** (was 119); ruff clean.
- New `frontend/` app at the repo root (npm). Phase 7 will later add a `frontend`
  Docker service + the FastAPI `BACKEND_URL` wiring; out of scope here.
- `docs/API_Spec.md` reconciled to the real routes (it had drifted from the
  implemented nesting and pagination).

---

## ADR-0012 — F4 Dashboard: cross-stock signal/sentiment views + portfolio analytics

**Date:** 2026-06-21
**Status:** Accepted

**Context:** PRD F4 requires four dashboard views. Market Overview (Phase 5.5) already
existed. The three remaining sub-dashboards — Forecast, Sentiment, Portfolio analytics —
required new API endpoints and frontend pages.

**Decision:**

- **`GET /market/signals`** — returns the latest 1-day XGBoost direction + confidence for
  every stock that has at least one forecast. Two nested subqueries: first to find the
  most recent `forecast_date` per stock (among rows with `direction IS NOT NULL`), then to
  take the nearest `target_date` from that batch (the horizon-1 signal). Keeps the
  response minimal — one row per stock.
- **`GET /market/sentiment`** — outer-joins `stocks → news_articles → sentiment_scores`
  and aggregates positive/negative/neutral counts per stock via `CASE` expressions.
  Stocks with no news return zeros (not omitted), so the table always shows all tracked
  symbols.
- **`GET /portfolios/{id}/analytics`** — computes annualized return, volatility (std dev
  × √252), Sharpe ratio (zero risk-free rate assumption), and max drawdown from the
  portfolio's price history. A new `PortfolioRepository.prices_for_stocks` method fetches
  365 days of prices for all holdings in one query; dates where any holding lacks a price
  are excluded before the daily-return series is built. Requires ≥ 20 complete dates;
  otherwise returns `null` for the time-series metrics (return_pct is always computed from
  cost/value).
- **Frontend** — two new pages (`/forecast`, `/sentiment`) added to the app shell nav;
  portfolio detail page gains a second row of analytics stat cards rendered only when the
  analytics query resolves.

**Modeling assumptions (portfolio analytics):**

- **Current allocation, not realized P&L.** The daily value series applies today's
  share counts across the whole window, so the volatility/Sharpe/drawdown figures
  describe the *current* allocation's risk profile, not the actually-held history
  (purchase/sale dates are ignored). `return_pct` is the only cost-basis-aware figure.
- **Risk-free rate = 0%** for Sharpe (annualized ×252 / ×√252); surfaced as a UI
  sub-label.
- Time-series metrics need ≥ 20 dates on which *every* holding has a price, over a
  365-day window; otherwise they return `null` (only `return_pct` is computed).

**Consequences:**

- Three new backend endpoints; no schema migrations required (reads only).
- `PortfolioAnalytics` dataclass lives in `portfolio/service.py` alongside
  `PortfolioValuation` — same ownership boundary.
- `GET /market/signals` keys its join on (stock, forecast_date, target_date), so a
  second directional model would collide; the result is de-duplicated to one
  signal per symbol (most confident wins) to keep the join dialect-agnostic
  (SQLite tests / Postgres prod) without `DISTINCT ON`.
- `get_analytics` runs **two queries** (portfolio load + one batched
  `prices_for_stocks`); it no longer calls `get_valued`, which had re-checked
  ownership and issued a per-holding `latest_close`. The latest close is taken as
  the newest bar in each holding's series, so `return_pct` now reflects the same
  365-day window as the risk metrics.
- Tests: `test_market.py` and `test_portfolios.py` extended (signals incl.
  multi-model dedup, sentiment, analytics incl. a hand-verified 25% drawdown).
  Full suite **146 passed** (was 133); ruff clean. `docs/API_Spec.md` updated with
  the three routes.
