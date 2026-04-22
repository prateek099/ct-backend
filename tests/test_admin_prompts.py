"""Tests for /api/v1/admin/prompts — admin-only prompt override management."""


def test_non_admin_cannot_list_overrides(client, auth_headers):
    res = client.get("/api/v1/admin/prompts/", headers=auth_headers)
    assert res.status_code == 403


def test_unauthenticated_cannot_list_overrides(client):
    res = client.get("/api/v1/admin/prompts/")
    assert res.status_code == 401


def test_admin_list_empty(client, admin_auth_headers):
    res = client.get("/api/v1/admin/prompts/", headers=admin_auth_headers)
    assert res.status_code == 200
    assert res.json() == []


def test_admin_get_missing_returns_404(client, admin_auth_headers):
    res = client.get("/api/v1/admin/prompts/ideas", headers=admin_auth_headers)
    assert res.status_code == 404


def test_admin_put_creates_override(client, admin_auth_headers):
    res = client.put(
        "/api/v1/admin/prompts/ideas",
        headers=admin_auth_headers,
        json={"system_prompt": "You are a custom idea bot."},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["tool"] == "ideas"
    assert body["system_prompt"] == "You are a custom idea bot."
    assert body["user_prompt_template"] is None


def test_admin_put_updates_existing(client, admin_auth_headers):
    client.put(
        "/api/v1/admin/prompts/script",
        headers=admin_auth_headers,
        json={"system_prompt": "v1"},
    )
    res = client.put(
        "/api/v1/admin/prompts/script",
        headers=admin_auth_headers,
        json={"system_prompt": "v2", "user_prompt_template": "template {title}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["system_prompt"] == "v2"
    assert body["user_prompt_template"] == "template {title}"


def test_admin_put_invalid_tool_rejected(client, admin_auth_headers):
    res = client.put(
        "/api/v1/admin/prompts/bogus",
        headers=admin_auth_headers,
        json={"system_prompt": "x"},
    )
    assert res.status_code == 422


def test_admin_history_records_every_put(client, admin_auth_headers):
    client.put(
        "/api/v1/admin/prompts/title",
        headers=admin_auth_headers,
        json={"system_prompt": "v1"},
    )
    client.put(
        "/api/v1/admin/prompts/title",
        headers=admin_auth_headers,
        json={"system_prompt": "v2"},
    )
    res = client.get(
        "/api/v1/admin/prompts/title/history", headers=admin_auth_headers
    )
    assert res.status_code == 200
    history = res.json()
    assert len(history) == 2
    # Prateek: newest first
    assert history[0]["system_prompt"] == "v2"
    assert history[1]["system_prompt"] == "v1"


def test_non_admin_cannot_put(client, auth_headers):
    res = client.put(
        "/api/v1/admin/prompts/seo",
        headers=auth_headers,
        json={"system_prompt": "x"},
    )
    assert res.status_code == 403


def test_override_applied_by_prompt_builder():
    """Direct test that build() honours system_override and template_override."""
    from app.prompts import ideas as ideas_prompt

    system, user = ideas_prompt.build(
        "Fitness tips",
        channel_context=None,
        system_override="CUSTOM SYSTEM",
        template_override="CUSTOM TEMPLATE topic={topic}{channel_block}",
    )
    assert system == "CUSTOM SYSTEM"
    assert user.startswith("CUSTOM TEMPLATE topic=Fitness tips")


def test_override_default_fallback_when_none():
    from app.prompts import ideas as ideas_prompt

    system_default, _ = ideas_prompt.build("Fitness", channel_context=None)
    system, _ = ideas_prompt.build(
        "Fitness", channel_context=None, system_override=None, template_override=None
    )
    assert system == system_default


def test_list_returns_all_tools_after_puts(client, admin_auth_headers):
    for tool in ["ideas", "script", "title", "seo"]:
        client.put(
            f"/api/v1/admin/prompts/{tool}",
            headers=admin_auth_headers,
            json={"system_prompt": f"system for {tool}"},
        )
    res = client.get("/api/v1/admin/prompts/", headers=admin_auth_headers)
    assert res.status_code == 200
    tools = {row["tool"] for row in res.json()}
    assert tools == {"ideas", "script", "title", "seo"}
