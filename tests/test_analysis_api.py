"""
Integration tests for the /api/analyze and /api/analyze-file endpoints.
"""
import io
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


SIMPLE_PYTHON = """
def sum_array(arr):
    total = 0
    for x in arr:
        total += x
    return total
"""

NESTED_LOOP_PYTHON = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(n - i - 1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
"""


# ===== VALID REQUESTS =====

async def test_analyze_basic(client):
    resp = await client.post("/api/analyze", json={"code": SIMPLE_PYTHON})
    assert resp.status_code == 200
    data = resp.json()
    assert "time_complexity" in data
    assert "space_complexity" in data
    assert "analysis_id" in data
    assert "language" in data


async def test_analyze_returns_required_fields(client):
    resp = await client.post("/api/analyze", json={"code": SIMPLE_PYTHON})
    data = resp.json()
    required = [
        "analysis_id", "language", "analysis_method", "provider_status",
        "time_complexity", "space_complexity", "case_analysis",
        "static_evidence", "explanation", "confidence"
    ]
    for field in required:
        assert field in data, f"Missing field: {field}"


async def test_analyze_with_language_override(client):
    resp = await client.post("/api/analyze", json={
        "code": SIMPLE_PYTHON,
        "language": "python"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["language"]["identifier"] == "python"
    assert data["language"]["detection_method"] == "user_selected"


async def test_analyze_nested_loops(client):
    resp = await client.post("/api/analyze", json={"code": NESTED_LOOP_PYTHON})
    assert resp.status_code == 200
    data = resp.json()
    tc = data["time_complexity"]["expression"]
    assert "n" in tc  # should detect some polynomial complexity


async def test_analyze_includes_static_evidence(client):
    resp = await client.post("/api/analyze", json={"code": SIMPLE_PYTHON})
    data = resp.json()
    ev = data["static_evidence"]
    assert "loops" in ev
    assert "parser_used" in ev


async def test_analyze_includes_visualization(client):
    resp = await client.post("/api/analyze", json={
        "code": SIMPLE_PYTHON,
        "settings": {"include_visualization": True}
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("visualization") is not None
    assert "curves" in data["visualization"]


async def test_analyze_confidence_is_valid(client):
    resp = await client.post("/api/analyze", json={"code": SIMPLE_PYTHON})
    conf = resp.json()["confidence"]
    assert conf in ("High", "Medium", "Low", "Unknown")


# ===== INVALID REQUESTS =====

async def test_analyze_empty_code(client):
    resp = await client.post("/api/analyze", json={"code": ""})
    assert resp.status_code == 422


async def test_analyze_whitespace_only(client):
    resp = await client.post("/api/analyze", json={"code": "   \n\t  "})
    assert resp.status_code == 422


async def test_analyze_missing_code_field(client):
    resp = await client.post("/api/analyze", json={"language": "python"})
    assert resp.status_code == 422


async def test_analyze_oversized_code(client):
    big_code = "x = 1\n" * 100_000  # ~700 KB
    resp = await client.post("/api/analyze", json={"code": big_code})
    assert resp.status_code == 413


async def test_analyze_unsupported_language_still_runs(client):
    # Should not crash; falls back to generic analysis
    resp = await client.post("/api/analyze", json={
        "code": "some code",
        "language": "generic"
    })
    assert resp.status_code == 200


# ===== FILE UPLOAD =====

async def test_analyze_file_python(client):
    file_content = SIMPLE_PYTHON.encode("utf-8")
    resp = await client.post(
        "/api/analyze-file",
        files={"file": ("test.py", file_content, "text/plain")},
    )
    assert resp.status_code == 200
    assert "time_complexity" in resp.json()


async def test_analyze_file_invalid_extension(client):
    resp = await client.post(
        "/api/analyze-file",
        files={"file": ("test.exe", b"binary content", "application/octet-stream")},
    )
    assert resp.status_code == 415


async def test_analyze_file_empty_content(client):
    resp = await client.post(
        "/api/analyze-file",
        files={"file": ("empty.py", b"", "text/plain")},
    )
    assert resp.status_code == 422


# ===== SECURITY: NO CODE EXECUTION =====

async def test_no_code_execution_malicious(client):
    """Verify that submitted code is analyzed, not executed."""
    malicious_code = """
import os
os.system('echo hacked > /tmp/pwned.txt')

def harmless():
    pass
"""
    # Should analyze without error (not execute)
    resp = await client.post("/api/analyze", json={"code": malicious_code, "language": "python"})
    # Must return a valid analysis, not execute the code
    assert resp.status_code == 200
    import os
    assert not os.path.exists("/tmp/pwned.txt"), "Code was executed! Security breach."


async def test_no_stack_trace_in_response(client):
    """Ensure stack traces are not returned to the browser."""
    resp = await client.post("/api/analyze", json={"code": ""})
    text = resp.text
    assert "Traceback" not in text
    assert "File \"" not in text or resp.status_code == 422
