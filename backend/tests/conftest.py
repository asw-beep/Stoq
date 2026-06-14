"""Pytest fixtures: an isolated in-memory SQLite DB and a TestClient.

These tests don't require Postgres or network access — the provider is faked and
the schema is created from the ORM metadata, so they run in CI without services.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.main import app
from db.base import Base, import_models
from db.session import get_db

import_models()


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def make_user(db_session):
    """Factory: create a persisted user and return it."""
    from auth.repository import UserRepository
    from core.security import hash_password

    repo = UserRepository(db_session)

    def _make(email: str = "user@example.com", password: str = "password123", role: str = "user"):
        user = repo.create(email=email, password_hash=hash_password(password), role=role)
        db_session.commit()
        return user

    return _make


@pytest.fixture()
def auth_headers(make_user):
    """A registered user's Bearer auth header for protected-endpoint requests."""
    from core.security import create_access_token

    user = make_user()
    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}
