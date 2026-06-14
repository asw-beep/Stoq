"""FastAPI auth/authorization dependencies.

These are the single choke points for "who is calling?" (authentication) and
"are they allowed?" (authorization). Endpoints depend on these rather than
re-implementing checks, so access control cannot drift between routes
(W-1 IDOR mitigation). See ADR-0002.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from fastapi import Depends, HTTPException, Path, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from auth.repository import UserRepository
from core.security import TokenError, decode_access_token
from db.session import get_db
from models.portfolio import Portfolio
from models.user import User

# auto_error=True => a missing/!Bearer Authorization header yields 401 before our
# code runs, satisfying "endpoints require auth". tokenUrl powers Swagger's
# Authorize button.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Resolve and validate the bearer token into the calling :class:`User`."""
    try:
        claims = decode_access_token(token)
        user_id = int(claims["sub"])
    except (TokenError, KeyError, ValueError):
        raise _CREDENTIALS_EXC from None

    user = UserRepository(db).get_by_id(user_id)
    if user is None:
        raise _CREDENTIALS_EXC
    return user


def require_role(*roles: str) -> Callable[[User], User]:
    """Dependency factory: allow only users whose role is in ``roles``."""
    allowed: Iterable[str] = set(roles)

    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient privileges",
            )
        return current_user

    return _dependency


def require_portfolio_owner(
    portfolio_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Portfolio:
    """Load a portfolio and assert the caller owns it.

    Centralized so every user-scoped portfolio endpoint shares one ownership
    rule (built ahead of those endpoints to pre-empt IDOR — W-1). Returns 404
    for both "missing" and "not yours" so existence is not disclosed to
    non-owners.
    """
    portfolio = db.get(Portfolio, portfolio_id)
    if portfolio is None or portfolio.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    return portfolio
