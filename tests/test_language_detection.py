"""
Tests for the language detection endpoint.
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_detect_python(client):
    code = "def bubble_sort(arr):\n    for i in range(len(arr)):\n        pass"
    resp = await client.post("/api/detect-language", json={"code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert data["language"] == "python"
    assert data["confidence"] in ("High", "Medium", "Low")


async def test_detect_python_by_filename(client):
    resp = await client.post("/api/detect-language",
                             json={"code": "x = 1", "filename": "script.py"})
    assert resp.status_code == 200
    assert resp.json()["language"] == "python"
    assert resp.json()["detection_method"] == "extension"


async def test_detect_javascript(client):
    code = "function foo() { const x = 1; let y = 2; console.log(x + y); }"
    resp = await client.post("/api/detect-language", json={"code": code})
    assert resp.status_code == 200
    # Should detect as js or a related language
    assert resp.json()["language"] in ("javascript", "typescript", "generic")


async def test_detect_java_by_extension(client):
    resp = await client.post("/api/detect-language",
                             json={"code": "public class Foo {}", "filename": "Foo.java"})
    assert resp.status_code == 200
    assert resp.json()["language"] == "java"


async def test_detect_empty_code(client):
    resp = await client.post("/api/detect-language", json={"code": ""})
    assert resp.status_code in (400, 422)


async def test_detect_whitespace_only(client):
    resp = await client.post("/api/detect-language", json={"code": "   \n\t  "})
    assert resp.status_code in (400, 422)


async def test_detect_returns_method(client):
    resp = await client.post("/api/detect-language",
                             json={"code": "def f(): pass", "filename": "x.py"})
    assert resp.status_code == 200
    assert "detection_method" in resp.json()
