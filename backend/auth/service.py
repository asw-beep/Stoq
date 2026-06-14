"""Authentication business logic (Service layer).

Orchestrates the user repository + security primitives. Knows nothing about
HTTP — it raises domain errors that the API layer maps to status codes.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from auth.repository import UserRepository
from core.security import create_access_token, hash_password, verify_password
from models.user import User

# Pre-computed bcrypt hash of a random string. Verified against when the email is
# unknown so login takes ~the same time whether or not the account exists.
_DUMMY_HASH = hash_password("user-enumeration-guard")


class EmailAlreadyRegisteredError(Exception):
    """Raised when registering an email that already exists."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials do not match a user."""


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = UserRepository(db)

    def register(self, email: str, password: str) -> User:
        """Create a new user, hashing the password. Caller commits the session."""
        email = email.strip().lower()
        if self.repo.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError(email)
        user = self.repo.create(email=email, password_hash=hash_password(password))
        return user

    def authenticate(self, email: str, password: str) -> User:
        """Return the user iff the email exists and the password verifies.

        The password is always verified (even for an unknown email, against a
        throwaway hash) to keep timing uniform and avoid leaking which emails
        are registered.
        """
        user = self.repo.get_by_email(email.strip().lower())
        password_ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)
        if user is None or not password_ok:
            raise InvalidCredentialsError()
        return user

    def issue_token(self, user: User) -> str:
        return create_access_token(subject=str(user.id))
