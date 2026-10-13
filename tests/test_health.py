"""
Tests for the health, language, and config endpoints.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_health_ok(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "ai_provider_configured" in data
    assert "analysis_modes" in data


async def test_health_includes_modes(client):
    resp = await client.get("/api/health")
    modes = resp.json()["analysis_modes"]
    assert "static_analysis" in modes or "fallback" in modes


async def test_languages_list(client):
    resp = await client.get("/api/languages")
    assert resp.status_code == 200
    data = resp.json()
    assert "languages" in data
    assert data["total"] > 0
    # Python must be in the list
    ids = [l["identifier"] for l in data["languages"]]
    assert "python" in ids


async def test_languages_have_required_fields(client):
    resp = await client.get("/api/languages")
    for lang in resp.json()["languages"]:
        assert "identifier" in lang
        assert "display_name" in lang
        assert "extensions" in lang
        assert "parser_available" in lang


async def test_config_status(client):
    resp = await client.get("/api/config/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "ai_provider_configured" in data
    assert "max_code_size_kb" in data
    assert data["max_code_size_kb"] > 0


async def test_config_no_secrets_exposed(client):
    resp = await client.get("/api/config/status")
    text = resp.text
    assert "api_key" not in text.lower()
    assert "secret" not in text.lower()
