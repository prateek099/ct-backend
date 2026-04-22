"""Tests for /api/v1/ideas — saved idea bank CRUD."""
import pytest


def _make_idea(title: str = "How to Meal Prep", **overrides) -> dict:
    body = {
        "title": title,
        "hook": "Prep once, eat all week.",
        "angle": "Beginner",
        "format": "Tutorial",
        "reasoning": "Audience loves actionable weekly wins.",
    }
    body.update(overrides)
    return body


def test_unauth_cannot_create(client):
    res = client.post("/api/v1/ideas/", json=_make_idea())
    assert res.status_code == 401


def test_create_and_list_idea(client, auth_headers):
    res = client.post("/api/v1/ideas/", json=_make_idea(), headers=auth_headers)
    assert res.status_code == 201
    created = res.json()
    assert created["title"] == "How to Meal Prep"
    assert created["hook"].startswith("Prep once")

    res = client.get("/api/v1/ideas/", headers=auth_headers)
    assert res.status_code == 200
    ideas = res.json()
    assert len(ideas) == 1
    assert ideas[0]["id"] == created["id"]


def test_duplicate_save_returns_existing_row(client, auth_headers):
    r1 = client.post("/api/v1/ideas/", json=_make_idea(), headers=auth_headers)
    r2 = client.post("/api/v1/ideas/", json=_make_idea(), headers=auth_headers)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]

    res = client.get("/api/v1/ideas/", headers=auth_headers)
    assert len(res.json()) == 1


def test_different_hook_creates_new_row(client, auth_headers):
    client.post(
        "/api/v1/ideas/", json=_make_idea(hook="a"), headers=auth_headers
    )
    client.post(
        "/api/v1/ideas/", json=_make_idea(hook="b"), headers=auth_headers
    )
    res = client.get("/api/v1/ideas/", headers=auth_headers)
    assert len(res.json()) == 2


def test_empty_title_rejected(client, auth_headers):
    res = client.post(
        "/api/v1/ideas/", json=_make_idea(title=""), headers=auth_headers
    )
    assert res.status_code == 422


def test_delete_idea(client, auth_headers):
    created = client.post(
        "/api/v1/ideas/", json=_make_idea(), headers=auth_headers
    ).json()
    res = client.delete(f"/api/v1/ideas/{created['id']}", headers=auth_headers)
    assert res.status_code == 204
    res = client.get("/api/v1/ideas/", headers=auth_headers)
    assert res.json() == []


def test_cannot_delete_other_users_idea(client, auth_headers, admin_auth_headers):
    created = client.post(
        "/api/v1/ideas/", json=_make_idea(), headers=auth_headers
    ).json()
    # Prateek: admin user is a different user — they shouldn't see a 403; just a 404.
    res = client.delete(
        f"/api/v1/ideas/{created['id']}", headers=admin_auth_headers
    )
    assert res.status_code == 404


def test_list_is_user_scoped(client, auth_headers, admin_auth_headers):
    client.post("/api/v1/ideas/", json=_make_idea(), headers=auth_headers)
    res = client.get("/api/v1/ideas/", headers=admin_auth_headers)
    assert res.status_code == 200
    assert res.json() == []


def test_pagination(client, auth_headers):
    for i in range(5):
        client.post(
            "/api/v1/ideas/",
            json=_make_idea(title=f"Idea {i}", hook=f"hook {i}"),
            headers=auth_headers,
        )
    res = client.get("/api/v1/ideas/?limit=2&offset=0", headers=auth_headers)
    assert len(res.json()) == 2
    res = client.get("/api/v1/ideas/?limit=2&offset=4", headers=auth_headers)
    assert len(res.json()) == 1
