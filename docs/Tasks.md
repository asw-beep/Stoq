# Phase 1

- [x] Initialize repo
- [x] Setup FastAPI
- [x] Setup PostgreSQL
- [x] Configure Alembic
- [x] Create database schema
- [x] Create Yahoo Finance ETL
- [x] Security test suite (backend/tests/test_security.py) encoding known gaps as strict-xfail gates

# Phase 1.5 — Security Hardening

Each task lists the test it turns green in backend/tests/test_security.py.

- [x] Stock symbol validation `^[A-Z0-9.-]{1,20}$` (path param + service layer) → `test_bad_symbol_rejected_with_422`, `test_service_rejects_bad_symbol_before_provider_call`
- [x] Startup secret check: reject `change-me`, require length ≥ 32 in production → `test_weak_secret_rejected_in_production`
- [x] Security-headers middleware (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, HSTS, CSP) → `test_security_headers_present`
- [x] `/health` stops disclosing `environment` → `test_health_does_not_disclose_environment`
- [x] Dockerfile runs as non-root user → `test_dockerfile_runs_as_non_root`
- [x] Remove `5432:5432` host port mapping from docker-compose → `test_compose_does_not_expose_postgres_to_host`
- [x] Remove the corresponding `xfail` markers once each test passes (see ADR-0006 for the symbol-validation test reconciliation)

# Phase 1.6 — Auth & Authorization

- [x] Password hashing service (`bcrypt`, used directly — passlib dropped, ADR-0007) → `test_password_service_hashes_and_verifies`
- [x] JWT issue/verify (python-jose) + token expiry (`core/security.py`)
- [x] `get_current_user` dependency; protect `/stocks` endpoints → `test_endpoints_require_auth`
- [x] Centralized ownership layer `require_portfolio_owner()` (built before any user-scoped endpoint exists)
- [x] Role-based authorization helper (`require_role()`)
- [x] Register/login/me endpoints (`/auth/*`, OAuth2 password flow)

# Phase 2

- [x] Technical indicators (`forecasting/features.py`: SMA, EMA, RSI, MACD, volatility)
- [x] Model evaluation (`forecasting/evaluation.py`: RMSE, MAE, MAPE)
- [x] Prophet forecasting (`forecasting/models/prophet_model.py`, behind `Forecaster` Protocol — ADR-0009)
- [x] Forecast endpoints reuse Phase 1.5 validation + Phase 1.6 auth from day one (`api/routers/forecasts.py`)
- [x] XGBoost forecasting (`forecasting/models/xgboost_model.py`, second `Forecaster` impl; model selected via `?model=` and the `build_forecaster` factory)

# Phase 3

- [x] News ingestion (`news/provider.py` Finnhub client)
- [x] FinBERT pipeline (`news/sentiment.py`)
- [x] Sentiment API (`api/routers/news.py`)

# Phase 4

- [x] Portfolio schema (`models/portfolio.py`)
- [x] Portfolio analytics (`portfolio/service.py` valuations)
- [x] Risk metrics (gain/loss, cost basis, market value)
- [x] All portfolio endpoints enforce ownership (service-layer `_owned_or_raise`)

# Phase 5

- [x] REST APIs
- [x] Validation
- [x] Error handling
- [x] Pagination on list endpoints (`Page[T]` envelope + `pagination_params`, ADR-0010)
- [x] Rate limiting (slowapi; login 5/min, register 3/min, expensive POSTs 5/min, 60/min global, ADR-0010)
- [x] Global exception sanitizer (no traceback/SQL leakage) → `test_error_body_has_no_internal_traces` stays green
- [x] Disable `/docs`, `/redoc`, `/openapi.json` in production (via `create_app` factory, ADR-0010)

# Phase 5.5 — additive read endpoints (ADR-0011)

- [x] `GET /stocks/{symbol}/prices?range=...` (OHLC series for charts)
- [x] `GET /market/overview` (latest close + day-over-day change per stock)

# Phase 6

- [x] Next.js setup (Next 16, TS, Tailwind v4, shadcn/ui [Base UI], TanStack Query, Recharts)
- [x] BFF auth: route-handler proxy + httpOnly cookie + `proxy.ts` guard (ADR-0011)
- [x] Dashboard pages (Market Overview, Stock detail, Portfolios list+detail, Account, login/register)
- [x] Charts (price+forecast line, sentiment bar, allocation donut)

# Phase 7

- [ ] Dockerize services
- [ ] Docker Compose

# Phase 8

- [ ] GitHub Actions
- [ ] Automated tests (pytest + ruff + security suite as a required gate, before deploy)

# Phase 9

- [ ] GCP Compute Engine deployment

# Phase 10

- [ ] Prometheus
- [ ] Grafana

# Phase 11

- [ ] Final documentation
- [ ] Architecture diagrams
- [ ] Resume bullet generation

# Phase 12 — DAST / OWASP ZAP Security Scan  ⚠️ IMPORTANT

Run last, against the fully-deployed stack, as a release gate before sign-off.

- [ ] ZAP baseline (passive) scan — verify Phase 1.5 security headers from the outside
- [ ] Authenticated active scan — drive ZAP with a JWT to cover auth + all user-scoped endpoints
- [ ] Confirm Phase 5 controls hold under scan (rate limiting, exception sanitizer, `/docs` disabled in prod)
- [ ] Exercise Phase 1.6 ownership/IDOR logic on portfolio/forecast endpoints
- [ ] Triage findings, fix, and re-scan until clean; optionally fold `zap-baseline.py` into Phase 8 CI
