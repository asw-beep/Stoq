# Security

This document describes the threat model, mitigations, and known limitations
for the Stoq backend, and how to run the regression suite that enforces them.

The full history of these decisions — including why each control was built
the way it was — is in [`docs/DECISIONS.md`](docs/DECISIONS.md).

## Threats considered

Derived from a pre-production architecture/threat review of the FastAPI
backend (`backend/`), tracked as a set of tests in
[`backend/tests/test_security.py`](backend/tests/test_security.py):

- **SQL injection** via user-controlled path parameters reaching the database.
- **Missing/insufficient authentication** on data endpoints (anonymous read access).
- **Missing input validation** on the `symbol` path parameter (oversized input,
  invalid charset, control characters, encoded newlines, Unicode) — including
  the case where an unvalidated symbol is forwarded to an outbound HTTP call
  (`yfinance`), which is SSRF-adjacent.
- **Reflected input** (e.g. an unknown symbol echoed into a 404 message)
  breaking out of its response context.
- **Weak or default secrets** (`SECRET_KEY`) being usable in production.
- **Plaintext or unhashed password storage.**
- **User enumeration via authentication timing** (a login attempt for a
  non-existent account taking a different code path/time than a real one).
- **Information disclosure** via `/health` (environment name, DB driver/DSN
  strings, credentials) or via error responses (stack traces, ORM/driver
  internals, file paths).
- **Missing security headers** (clickjacking, MIME-sniffing, referrer leakage).
- **Container/infrastructure hardening gaps** — running as root, exposing the
  database port to the host network.

## Mitigations in place

Each item below is enforced by a named, currently-passing test (mostly in
`backend/tests/test_security.py`, one in `backend/tests/test_auth.py` as
noted) and fails the suite if it regresses:

| Mitigation | Test(s) |
|---|---|
| SQL injection is not possible — all queries go through SQLAlchemy's parameterized ORM, proven by feeding classic injection payloads into `/stocks/{symbol}` and confirming no 500, no data leak, and the table survives intact | `test_sqli_payload_never_leaks_or_breaks` |
| Symbol input is validated (`^[A-Z0-9.-]{1,20}$`) at the API boundary — oversized, invalid-charset, control-character, and Unicode input is rejected with 422, never crashes the process | `test_bad_symbol_does_not_500`, `test_bad_symbol_rejected_with_422` |
| Symbol validation is also enforced at the service layer, *before* any outbound call to the market-data provider, so a malicious symbol never reaches the external HTTP request | `test_service_rejects_bad_symbol_before_provider_call` |
| Reflected/rejected input is always returned as safely JSON-encoded, never in a context where it could execute or break out of the response | `test_reflected_symbol_is_json_encoded`, `test_invalid_symbol_error_is_json_encoded` |
| Data endpoints require a valid Bearer JWT; anonymous requests get 401 | `test_endpoints_require_auth` |
| A weak/placeholder `SECRET_KEY` (e.g. `"change-me"`, `"use-openssl..."`, or anything under 32 characters) is rejected at startup when `ENVIRONMENT=production` | `test_weak_secret_rejected_in_production` |
| Passwords are hashed with `bcrypt` (never stored or compared in plaintext) | `test_password_service_hashes_and_verifies` |
| Login compares against a dummy bcrypt hash when the email doesn't exist (`_DUMMY_HASH` in `backend/auth/service.py`), so a login attempt takes the same code path regardless of account existence (mitigates user-enumeration via timing/response-shape) | `test_authenticate_unknown_email` (`backend/tests/test_auth.py`) |
| `/health` never discloses the environment name or any credential/DSN-shaped string | `test_health_does_not_disclose_environment`, `test_health_never_leaks_secrets` |
| Standard security headers are set on every response: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Strict-Transport-Security`, `Content-Security-Policy` | `test_security_headers_present` (`backend/api/main.py`) |
| Error responses never leak internals — no tracebacks, ORM/driver names, or filesystem paths | `test_error_body_has_no_internal_traces` |
| The Docker image runs as an unprivileged user (`appuser`, uid 10001), never root | `test_dockerfile_runs_as_non_root` |
| PostgreSQL is not published to the host network in `docker-compose.yml` | `test_compose_does_not_expose_postgres_to_host` |

Additional controls that exist in the code but aren't exercised by
`test_security.py` directly (covered by other test modules):
rate limiting (`slowapi` — 60/min global, 5/min on login, 3/min on register,
5/min on expensive POST endpoints), interactive API docs (`/docs`, `/redoc`,
`/openapi.json`) disabled when `ENVIRONMENT=production`, pagination bounds on
list endpoints, and centralized ownership checks (`require_portfolio_owner`,
`require_role`) so one user cannot read or modify another user's data.

## Known limitations

- The regression suite runs against SQLite in-memory for speed; some
  Postgres-specific behavior (e.g. `ON CONFLICT`, numeric precision) is not
  re-verified under the real database engine in this suite.
- There is no automated dynamic (DAST) scan yet — an authenticated OWASP ZAP
  pass against a deployed instance is planned but not yet run (see
  `docs/Roadmap.md`, Phase 12).
- No automated dependency/SCA scanning (e.g. `pip-audit`, `npm audit` in CI)
  is wired up yet.
- No CI pipeline currently runs this suite automatically on every push —
  it must be run locally today (Phase 8 in `docs/Roadmap.md` will make it a
  required gate).
- CSRF is not applicable to the current API (Bearer-token auth, no
  cookie-based session on the backend itself), but this should be
  re-evaluated if cookie-based auth is ever added directly to the backend.

## How to run the security suite

```bash
cd backend
uv run pytest tests/test_security.py -v
```

(Run the full suite with `uv run pytest` from `backend/`.)
