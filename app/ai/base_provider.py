"""
Abstract base class for all AI providers.
Every provider must implement `analyze`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class AIAnalysisResult:
    """Typed result from an AI provider."""

    def __init__(
        self,
        time_complexity: str,
        space_complexity: str,
        explanation: str,
        best_case: Optional[str] = None,
        average_case: Optional[str] = None,
        worst_case: Optional[str] = None,
        assumptions: Optional[list] = None,
        optimizations: Optional[list] = None,
        confidence: str = "Medium",
        warnings: Optional[list] = None,
        provider: str = "unknown",
        model: Optional[str] = None,
        is_fallback: bool = False,
        raw: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.time_complexity = time_complexity
        self.space_complexity = space_complexity
        self.explanation = explanation
        self.best_case = best_case
        self.average_case = average_case
        self.worst_case = worst_case
        self.assumptions = assumptions or []
        self.optimizations = optimizations or []
        self.confidence = confidence
        self.warnings = warnings or []
        self.provider = provider
        self.model = model
        self.is_fallback = is_fallback
        self.raw = raw or {}


class BaseAIProvider(ABC):
    """Interface that every AI provider adapter must implement."""

    @abstractmethod
    async def analyze(
        self,
        code: str,
        language: str,
        static_summary: str,
    ) -> AIAnalysisResult:
        """
        Send the code and static analysis evidence to an AI model and
        return a validated, structured result.

        Parameters
        ----------
        code:
            The original source code submitted by the user.
        language:
            The detected/selected programming language identifier.
        static_summary:
            A text summary of the static-analysis findings.

        Returns
        -------
        AIAnalysisResult
            Structured output conforming to the response schema.
        """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name, e.g. 'openai'."""

    @property
    def is_fallback(self) -> bool:
        return False
