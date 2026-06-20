"""Admin endpoint tests: role-gating and the user listing."""

from __future__ import annotations

from core.security import create_access_token


def _headers_for(user) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(subject=str(user.id))}"}


def test_list_users_requires_auth(client):
    assert client.get("/admin/users").status_code == 401


def test_list_users_forbidden_for_plain_user(client, make_user):
    user = make_user(email="plain@example.com", role="user")
    resp = client.get("/admin/users", headers=_headers_for(user))
    assert resp.status_code == 403


def test_admin_lists_all_users_without_password_hash(client, make_user):
    make_user(email="alice@example.com", role="user")
    admin = make_user(email="admin@example.com", role="admin")

    resp = client.get("/admin/users", headers=_headers_for(admin))
    assert resp.status_code == 200
    body = resp.json()

    assert body["total"] == 2
    emails = {item["email"] for item in body["items"]}
    assert emails == {"alice@example.com", "admin@example.com"}
    # The hash must never be serialized to the client.
    for item in body["items"]:
        assert "password_hash" not in item
        assert {"id", "email", "role", "created_at"} <= item.keys()


def test_list_users_pagination(client, make_user):
    admin = make_user(email="admin@example.com", role="admin")
    for i in range(3):
        make_user(email=f"u{i}@example.com", role="user")

    resp = client.get("/admin/users?limit=2&offset=0", headers=_headers_for(admin))
    body = resp.json()
    assert resp.status_code == 200
    assert body["total"] == 4  # 3 users + the admin
    assert len(body["items"]) == 2
