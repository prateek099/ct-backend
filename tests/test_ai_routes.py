"""Tests for the 4 AI endpoints — video-idea-gen, script-generator, title-suggestor, seo-description.

Mocks out `track_openai_call` so no real OpenAI traffic. Covers the happy path
and one validation-error path per endpoint. All AI routes require auth via
`get_optional_user`, so tests pass the shared `auth_headers` fixture.
"""
from unittest.mock import patch


# ── /video-idea-gen ────────────────────────────────────────────────────────────

def test_video_idea_gen_happy_path(client, auth_headers):
    fake = {"ideas": [{"title": "Idea 1"}, {"title": "Idea 2"}]}
    with patch("app.api.routes.video_idea_gen.track_openai_call", return_value=fake):
        res = client.post("/api/v1/video-idea-gen",
                          json={"prompt": "Fitness tips"}, headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["prompt"] == "Fitness tips"
    assert body["response"] == fake


def test_video_idea_gen_empty_prompt(client, auth_headers):
    res = client.post("/api/v1/video-idea-gen",
                      json={"prompt": "   "}, headers=auth_headers)
    assert res.status_code == 400


# ── /script-generator ──────────────────────────────────────────────────────────

def test_script_generator_happy_path(client, auth_headers):
    fake = {
        "word_count": 1200,
        "estimated_duration_seconds": 540,
        "sections": [{"name": "Hook", "content": "Opener"}],
        "full_script": "full",
    }
    with patch("app.api.routes.script_generator.track_openai_call", return_value=fake):
        res = client.post("/api/v1/script-generator", json={
            "title": "Title", "hook": "Hook line",
            "angle": "Beginner", "format": "Tutorial",
        }, headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["title"] == "Title"
    assert body["script"]["word_count"] == 1200


def test_script_generator_empty_title(client, auth_headers):
    res = client.post("/api/v1/script-generator", json={
        "title": "  ", "hook": "h", "angle": "a", "format": "f",
    }, headers=auth_headers)
    assert res.status_code == 400


def test_script_generator_no_sections(client, auth_headers):
    with patch("app.api.routes.script_generator.track_openai_call", return_value={"sections": []}):
        res = client.post("/api/v1/script-generator", json={
            "title": "T", "hook": "h", "angle": "a", "format": "f",
        }, headers=auth_headers)
    assert res.status_code == 500


# ── /title-suggestor ───────────────────────────────────────────────────────────

def test_title_suggestor_happy_path(client, auth_headers):
    fake = {"titles": [{
        "title": f"T{i}", "style": "Listicle", "ctr_angle": "Curiosity",
        "search_intent": "learn", "seo_keywords": ["k"], "reasoning": "r",
    } for i in range(10)]}
    with patch("app.api.routes.title_suggestor.track_openai_call", return_value=fake):
        res = client.post("/api/v1/title-suggestor",
                          json={"topic": "A topic"}, headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()["titles"]) == 10


def test_title_suggestor_empty_topic(client, auth_headers):
    res = client.post("/api/v1/title-suggestor",
                      json={"topic": ""}, headers=auth_headers)
    assert res.status_code == 400


# ── /seo-description ───────────────────────────────────────────────────────────

def test_seo_description_happy_path(client, auth_headers):
    fake = {
        "description": "A solid description.",
        "description_word_count": 3,
        "hashtags": ["#a", "#b", "#c", "#d", "#e"],
        "tags": "one, two, three",
        "tags_char_count": 15,
        "primary_keyword": "kw",
        "secondary_keywords": ["k1", "k2"],
    }
    with patch("app.api.routes.seo_description.track_openai_call", return_value=fake):
        res = client.post("/api/v1/seo-description", json={
            "title": "T", "topic": "Fitness",
        }, headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["primary_keyword"] == "kw"
    assert body["tags_char_count"] == 15


def test_seo_description_empty_title(client, auth_headers):
    res = client.post("/api/v1/seo-description",
                      json={"title": " ", "topic": "x"}, headers=auth_headers)
    assert res.status_code == 400


def test_seo_description_trims_oversized_tags(client, auth_headers):
    long_tags = ", ".join([f"tag{i}" for i in range(200)])  # > 500 chars
    fake = {
        "description": "ok",
        "description_word_count": 1,
        "hashtags": [],
        "tags": long_tags,
        "tags_char_count": len(long_tags),
        "primary_keyword": "",
        "secondary_keywords": [],
    }
    with patch("app.api.routes.seo_description.track_openai_call", return_value=fake):
        res = client.post("/api/v1/seo-description",
                          json={"title": "T", "topic": "x"}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["tags_char_count"] <= 500
