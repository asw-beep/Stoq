"""Data access for user accounts (Repository pattern)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.user import User


class UserRepository:
    """Encapsulates all DB access for :class:`User` rows."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def create(self, email: str, password_hash: str, role: str = "user") -> User:
        user = User(email=email, password_hash=password_hash, role=role)
        self.db.add(user)
        self.db.flush()  # assign PK without committing (let the caller own the txn)
        return user
