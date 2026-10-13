"""
Tests for the AI provider layer (mock provider).
"""
import pytest

from app.ai.mock_provider import MockProvider
from app.ai.provider_factory import get_provider


async def test_mock_provider_returns_result():
    provider = MockProvider()
    result = await provider.analyze(
        code="def f(n):\n    for i in range(n): pass",
        language="Python",
        static_summary="Time complexity: O(n)\nSpace complexity: O(1)",
    )
    assert result.time_complexity
    assert result.space_complexity
    assert result.is_fallback is True
    assert result.provider == "mock_fallback"


async def test_mock_provider_explanation_labels_fallback():
    provider = MockProvider()
    result = await provider.analyze(
        code="x = 1",
        language="Python",
        static_summary="Time complexity: O(1)\nSpace complexity: O(1)",
    )
    assert "FALLBACK" in result.explanation or "fallback" in result.explanation.lower()


async def test_mock_provider_not_real_ai():
    provider = MockProvider()
    result = await provider.analyze(
        code="x = 1",
        language="Python",
        static_summary="",
    )
    assert result.is_fallback is True
    assert result.model is None


async def test_provider_factory_returns_mock_without_key(monkeypatch):
    """Without a valid API key, provider factory should return MockProvider."""
    from app.config import get_settings, Settings
    # Patch settings to have no API key
    monkeypatch.setattr("app.config.get_settings", lambda: Settings(
        ai_api_key="",
        ai_provider="mock",
    ))
    # Clear the lru_cache
    get_settings.cache_clear()
    provider = get_provider()
    from app.ai.mock_provider import MockProvider
    assert isinstance(provider, MockProvider)
    get_settings.cache_clear()


async def test_mock_provider_name():
    provider = MockProvider()
    assert provider.provider_name == "mock_fallback"
    assert provider.is_fallback is True
