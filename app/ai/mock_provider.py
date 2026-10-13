"""
Mock AI provider for fallback/demo mode.
Returns deterministic, rule-enriched results without any external API call.
Clearly labeled as non-AI analysis.
"""
from __future__ import annotations

from app.ai.base_provider import AIAnalysisResult, BaseAIProvider


class MockProvider(BaseAIProvider):
    """
    Deterministic fallback provider.
    Uses the static analysis evidence passed in the static_summary
    to construct a clearly labeled non-AI response.
    """

    @property
    def provider_name(self) -> str:
        return "mock_fallback"

    @property
    def is_fallback(self) -> bool:
        return True

    async def analyze(
        self,
        code: str,
        language: str,
        static_summary: str,
    ) -> AIAnalysisResult:
        """
        Return a fallback result derived from static analysis alone.
        No external API is called. The result is clearly labeled as a fallback.
        """
        # Extract key metrics from the static_summary text
        time_expr = _extract_from_summary(static_summary, "Time complexity:")
        space_expr = _extract_from_summary(static_summary, "Space complexity:")
        worst = _extract_from_summary(static_summary, "Worst case:")
        best = _extract_from_summary(static_summary, "Best case:")
        avg = _extract_from_summary(static_summary, "Average case:")

        explanation = (
            f"[FALLBACK MODE — No AI provider configured]\n\n"
            f"This result is based on static structural analysis of the {language} code. "
            f"No external AI model was consulted. Complexity estimates are derived from "
            f"loop structure, recursion patterns, sorting calls, and heuristic rules.\n\n"
            f"Static analysis summary:\n{static_summary}\n\n"
            f"To enable AI-assisted analysis, configure an AI provider in your .env file "
            f"(see .env.example for details)."
        )

        return AIAnalysisResult(
            time_complexity=time_expr or "O(n)",
            space_complexity=space_expr or "O(1)",
            explanation=explanation,
            best_case=best,
            average_case=avg,
            worst_case=worst,
            assumptions=[
                "Result based on static analysis only — no AI model was used.",
                "Assumes n represents the primary input size.",
            ],
            optimizations=[],
            confidence="Low",
            warnings=[
                "FALLBACK MODE: AI analysis unavailable. Configure AI_API_KEY for enhanced results.",
                "These estimates are heuristic and may be inaccurate for complex code patterns.",
            ],
            provider="mock_fallback",
            model=None,
            is_fallback=True,
        )


def _extract_from_summary(summary: str, key: str) -> str:
    """Simple key-value extraction from formatted summary text."""
    for line in summary.splitlines():
        if line.startswith(key):
            value = line[len(key):].strip()
            return value
    return ""
