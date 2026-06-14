"""Auth & authorization tests: register/login flow, token validation,
ownership and role dependencies."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from auth.dependencies import (
    get_current_user,
    require_portfolio_owner,
    require_role,
)
from auth.service import (
    AuthService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
)
from core.security import create_access_token, hash_password
from models.portfolio import Portfolio
from models.user import User


# --------------------------------------------------------------------------- #
# Service layer
# --------------------------------------------------------------------------- #
def test_register_then_authenticate(db_session):
    service = AuthService(db_session)
    user = service.register("New@Example.com", "password123")
    db_session.commit()

    assert user.email == "new@example.com"  # normalized
    assert user.password_hash != "password123"

    same = service.authenticate("new@example.com", "password123")
    assert same.id == user.id


def test_register_duplicate_email_rejected(db_session):
    service = AuthService(db_session)
    service.register("dup@example.com", "password123")
    db_session.commit()
    with pytest.raises(EmailAlreadyRegisteredError):
        service.register("dup@example.com", "password123")


def test_authenticate_wrong_password(db_session):
    service = AuthService(db_session)
    service.register("a@example.com", "password123")
    db_session.commit()
    with pytest.raises(InvalidCredentialsError):
        service.authenticate("a@example.com", "wrong-password")


def test_authenticate_unknown_email(db_session):
    service = AuthService(db_session)
    with pytest.raises(InvalidCredentialsError):
        service.authenticate("ghost@example.com", "whatever123")


# --------------------------------------------------------------------------- #
# HTTP endpoints
# --------------------------------------------------------------------------- #
def test_register_and_login_endpoints(client):
    r = client.post("/auth/register", json={"email": "x@example.com", "password": "password123"})
    assert r.status_code == 201
    assert r.json()["email"] == "x@example.com"
    assert "password" not in r.json() and "password_hash" not in r.json()

    r = client.post("/auth/login", data={"username": "x@example.com", "password": "password123"})
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert r.json()["token_type"] == "bearer"

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "x@example.com"


def test_register_duplicate_returns_409(client):
    body = {"email": "dupe@example.com", "password": "password123"}
    assert client.post("/auth/register", json=body).status_code == 201
    assert client.post("/auth/register", json=body).status_code == 409


def test_login_bad_password_returns_401(client):
    client.post("/auth/register", json={"email": "y@example.com", "password": "password123"})
    r = client.post("/auth/login", data={"username": "y@example.com", "password": "nope"})
    assert r.status_code == 401


def test_short_password_rejected_422(client):
    r = client.post("/auth/register", json={"email": "z@example.com", "password": "short"})
    assert r.status_code == 422


def test_me_with_garbage_token_401(client):
    r = client.get("/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401


def test_protected_stock_endpoint_with_token(client, auth_headers):
    assert client.get("/stocks", headers=auth_headers).status_code == 200


# --------------------------------------------------------------------------- #
# get_current_user dependency
# --------------------------------------------------------------------------- #
def test_get_current_user_for_deleted_user_401(db_session):
    token = create_access_token(subject="424242")  # no such user row
    with pytest.raises(HTTPException) as exc:
        get_current_user(token=token, db=db_session)
    assert exc.value.status_code == 401


# --------------------------------------------------------------------------- #
# require_role dependency factory
# --------------------------------------------------------------------------- #
def test_require_role_allows_and_forbids():
    admin = User(id=1, email="a@x.com", password_hash="h", role="admin")
    plain = User(id=2, email="b@x.com", password_hash="h", role="user")

    admin_only = require_role("admin")
    assert admin_only(current_user=admin) is admin
    with pytest.raises(HTTPException) as exc:
        admin_only(current_user=plain)
    assert exc.value.status_code == 403


# --------------------------------------------------------------------------- #
# require_portfolio_owner — centralized IDOR guard
# --------------------------------------------------------------------------- #
def test_require_portfolio_owner_allows_owner_blocks_others(db_session):
    owner = User(email="owner@x.com", password_hash=hash_password("password123"))
    other = User(email="other@x.com", password_hash=hash_password("password123"))
    db_session.add_all([owner, other])
    db_session.flush()
    pf = Portfolio(user_id=owner.id, name="Mine")
    db_session.add(pf)
    db_session.commit()

    # Owner gets the portfolio back.
    assert require_portfolio_owner(pf.id, current_user=owner, db=db_session) is pf

    # Non-owner gets 404 (existence not disclosed), not 403.
    with pytest.raises(HTTPException) as exc:
        require_portfolio_owner(pf.id, current_user=other, db=db_session)
    assert exc.value.status_code == 404

    # Missing portfolio -> 404.
    with pytest.raises(HTTPException) as exc:
        require_portfolio_owner(999, current_user=owner, db=db_session)
    assert exc.value.status_code == 404
