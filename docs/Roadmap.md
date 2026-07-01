# Roadmap

Phase 1
Data Layer  ✅ complete

Phase 1.5  (NEW)  ✅ complete
Security Hardening — gated by backend/tests/test_security.py
(input validation, secret-strength enforcement, security headers,
/health hardening, non-root container, no host-exposed Postgres)

Phase 1.6  (NEW)  ✅ complete
Auth & Authorization Framework
(JWT, password hashing, current-user dependency, centralized ownership checks)

Phase 2  ✅ complete
Forecasting Engine
(technical indicators, Prophet + XGBoost behind a Forecaster Protocol,
RMSE/MAE/MAPE evaluation, auth+validated forecast endpoints — ADR-0009)

Phase 3  ✅ complete
Sentiment Engine (news ingestion + FinBERT scoring)

Phase 4  ✅ complete
Portfolio Analytics

Phase 5  ✅ complete
Backend APIs (pagination, rate limiting, global exception sanitizer,
docs disabled in prod — ADR-0010)

Phase 5.5  ✅ complete
Additive read endpoints (prices series + market overview — ADR-0011)

Phase 6  ✅ complete
Frontend Dashboard (Next.js 16 BFF + httpOnly cookie auth, light theme — ADR-0011)

Phase 7
Dockerization

Phase 8
CI/CD — runs pytest + ruff + the security suite as a required gate (precedes deploy)

Phase 9
GCP Deployment

Phase 10
Monitoring

Phase 11
Documentation

Phase 12  ⚠️ IMPORTANT
DAST / OWASP ZAP Security Scan — full authenticated active scan against the
deployed stack (passive header check + active scan of auth and all user-scoped
endpoints). Run last so every endpoint, the Phase 5 controls (rate limiting,
exception sanitizer, docs-disabled-in-prod) and the Phase 1.6 ownership/IDOR
logic are all in place and exercisable. Findings feed back as fixes before sign-off.

---

## Sequencing notes

- Phase 1.5/1.6 are inserted ahead of feature work: the security review rated
  auth, input validation, and secret enforcement as P0. Every later phase that
  creates user-scoped data (2, 4) is then born authenticated rather than
  retrofitted — this pre-empts the IDOR risk flagged in the review.
- CI/CD (Phase 8) precedes the first real GCP deploy (Phase 9) so the security
  suite acts as a required gate and weak secrets / regressions cannot ship.
- DAST/ZAP (Phase 12) is deliberately last: a passive header scan is possible
  today, but the active scan is only meaningful once Phase 5 (rate limiting,
  exception sanitizer, docs disabled in prod) and the user-scoped Phase 2/4
  endpoints exist — otherwise it just re-reports known/expected gaps. Treated as
  a release gate before sign-off, not an afterthought.
- Definition of done for 1.5/1.6 = the corresponding strict-xfail tests in
  backend/tests/test_security.py flip to passing (and their markers are removed).
