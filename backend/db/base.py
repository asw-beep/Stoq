"""Declarative base and metadata.

`Base` is the shared declarative base for all ORM models. `import_models()` is
used by Alembic's env so that all model modules are registered on the metadata
before autogenerate runs.
"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class TimestampMixin:
    """Adds a server-managed created_at column."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


def import_models() -> None:
    """Import all model modules so they register on Base.metadata.

    Called by Alembic env and at app startup. Keep this in sync with new models.
    """
    from models import (  # noqa: F401
        forecast,
        news,
        portfolio,
        stock,
        user,
    )
