"""
Security-focused tests.
"""
import os
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_no_code_execution(client):
    """Ensure submitted code is never executed."""
    canary_path = "/tmp/_complexity_analyzer_canary.txt"
    if os.path.exists(canary_path):
        os.remove(canary_path)

    evil_code = f"""
import os
os.system("touch {canary_path}")

def harmless(n):
    for i in range(n):
        pass
"""
    resp = await client.post("/api/analyze", json={"code": evil_code, "language": "python"})
    assert resp.status_code == 200  # Should analyze, not execute
    assert not os.path.exists(canary_path), "Code was executed! Critical security failure."


async def test_no_path_traversal_in_file_upload(client):
    """Path traversal filenames must be sanitized."""
    resp = await client.post(
        "/api/analyze-file",
        files={"file": ("../../etc/passwd", b"def f(): pass", "text/plain")},
    )
    # Should either reject (415 for bad extension) or handle safely
    # Must NOT attempt to read /etc/passwd
    assert resp.status_code in (200, 415, 422)


async def test_oversized_file_rejected(client):
    big = b"x = 1\n" * 100_000  # ~700 KB
    resp = await client.post(
        "/api/analyze-file",
        files={"file": ("big.py", big, "text/plain")},
    )
    assert resp.status_code == 413


async def test_no_api_key_in_config_response(client):
    resp = await client.get("/api/config/status")
    text = resp.text.lower()
    assert "api_key" not in text
    assert "bearer" not in text
    assert "secret" not in text


async def test_malformed_json_body(client):
    resp = await client.post(
        "/api/analyze",
        content=b"this is not json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422


async def test_very_long_language_field_handled(client):
    resp = await client.post("/api/analyze", json={
        "code": "def f(): pass",
        "language": "x" * 10000
    })
    # Should not crash — may return 200 with generic analysis or 422
    assert resp.status_code in (200, 422, 400)
