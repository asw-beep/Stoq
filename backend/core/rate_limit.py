"""Application rate limiter (Phase 5, ADR-0010).

Defined in its own module so routers can import ``limiter`` and decorate their
endpoints without importing ``api.main`` (which imports the routers — that would
be a cycle). ``api.main`` is responsible for registering the limiter on the app
(state, exception handler, middleware).

Keyed per client IP. A permissive global default guards every route; specific
endpoints (auth, expensive POSTs) apply stricter per-route limits via the
``@limiter.limit(...)`` decorator.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# Global default applied to every route via SlowAPIMiddleware; per-route
# decorators override this for sensitive endpoints.
DEFAULT_LIMITS = ["60/minute"]

limiter = Limiter(key_func=get_remote_address, default_limits=DEFAULT_LIMITS)
