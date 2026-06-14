"""Security primitives: password hashing and JWT access tokens.

Pure, dependency-light helpers (no DB, no FastAPI) so they can be unit-tested in
isolation and reused by the auth service and the request dependencies.
See ADR-0002 (auth) and docs/ARCHITECTURE_FOR_SECURITY_TESTING.txt (W-1, W-10).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from core.config import get_settings

# bcrypt hashes only the first 72 bytes of input; truncate explicitly so the same
# rule applies to hashing and verifying and bcrypt never raises on long inputs.
_BCRYPT_MAX_BYTES = 72


class TokenError(Exception):
    """Raised when a JWT is missing, malformed, expired, or otherwise invalid."""


def _prepare(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Return a salted bcrypt hash of ``password`` (``$2b$...``)."""
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Constant-time check of a plaintext password against a stored hash."""
    try:
        return bcrypt.checkpw(_prepare(plain_password), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(
    subject: str, expires_delta: timedelta | None = None
) -> str:
    """Issue a signed JWT whose ``sub`` claim identifies the principal."""
    settings = get_settings()
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    now = datetime.now(UTC)
    claims = {"sub": str(subject), "iat": now, "exp": now + expires_delta}
    return jwt.encode(claims, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Verify signature + expiry and return the token claims.

    Raises :class:`TokenError` for any invalid token so callers never have to
    catch the low-level ``jose`` exception types.
    """
    settings = get_settings()
    try:
        return jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:  # expired, bad signature, malformed, ...
        raise TokenError(str(exc)) from exc
