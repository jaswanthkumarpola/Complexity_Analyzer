"""
Provider factory: selects and instantiates the appropriate AI provider
based on application configuration.
"""
from __future__ import annotations

import logging

from app.ai.base_provider import BaseAIProvider
from app.config import get_settings

logger = logging.getLogger(__name__)


def get_provider() -> BaseAIProvider:
    """
    Return the configured AI provider.

    Selection logic:
    1. If AI_PROVIDER=mock → always return MockProvider (useful for tests/demo).
    2. If AI_API_KEY is set and non-placeholder → return LLMProvider.
    3. Otherwise → fall back to MockProvider and log a warning.
    """
    settings = get_settings()

    if settings.ai_provider == "mock":
        from app.ai.mock_provider import MockProvider
        logger.info("AI provider: mock (explicitly configured)")
        return MockProvider()

    if settings.ai_provider_configured:
        from app.ai.llm_provider import LLMProvider
        logger.info(
            "AI provider: %s (model: %s)", settings.ai_provider, settings.ai_model
        )
        return LLMProvider()

    # Fallback
    from app.ai.mock_provider import MockProvider
    logger.warning(
        "No valid AI_API_KEY configured. Falling back to mock provider. "
        "Set AI_API_KEY in your .env file to enable AI-assisted analysis."
    )
    return MockProvider()
