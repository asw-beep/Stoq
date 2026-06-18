"""Shared pagination params for list endpoints (Phase 5, ADR-0010).

A single FastAPI dependency so every paginated endpoint enforces the same
bounds. Out-of-range values are rejected with 422 at the edge, matching the
Phase 1.5 "validate at the boundary" contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query

# Upper bound on page size; keeps response payloads and DB scans bounded.
MAX_PAGE_LIMIT = 200
DEFAULT_PAGE_LIMIT = 50


@dataclass
class Pagination:
    limit: int
    offset: int


def pagination_params(
    limit: int = Query(DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(0, ge=0),
) -> Pagination:
    return Pagination(limit=limit, offset=offset)
