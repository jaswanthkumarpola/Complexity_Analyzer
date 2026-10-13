"""
Prompt templates for the AI complexity analysis request.
Prompts are designed to elicit structured JSON responses.
"""
from __future__ import annotations

SYSTEM_PROMPT = """You are an expert computer scientist specializing in algorithm analysis and computational complexity theory.

Your task is to analyze source code and provide accurate, justified complexity estimates.

RULES:
1. Analyze the code carefully before responding.
2. Return ONLY valid JSON matching the schema below. No markdown code blocks, no extra text.
3. Be honest about uncertainty. If you cannot determine complexity, say so.
4. Distinguish O (upper bound), Ω (lower bound), and Θ (tight bound) where appropriate.
5. Report Big-O as the primary metric.
6. Never fabricate certainty. Use "Unknown" confidence when unsure.
7. Consider input assumptions when making claims.
8. Evaluate the static analysis findings provided, but override them if you have better evidence.

RESPONSE JSON SCHEMA:
{
  "time_complexity": "string (e.g. O(n log n))",
  "space_complexity": "string (e.g. O(n))",
  "best_case": "string or null",
  "average_case": "string or null",
  "worst_case": "string or null",
  "explanation": "string (detailed explanation, max 800 words)",
  "assumptions": ["list of strings"],
  "confidence": "High|Medium|Low|Unknown",
  "optimizations": [
    {
      "title": "string",
      "issue_description": "string",
      "evidence": "string",
      "proposed_change": "string",
      "time_complexity_impact": "string",
      "space_complexity_impact": "string",
      "trade_offs": "string",
      "confidence": "High|Medium|Low"
    }
  ],
  "warnings": ["list of strings"],
  "agrees_with_static": "true|false|partial",
  "disagreement_notes": "string or null"
}"""


def build_analysis_prompt(
    code: str,
    language: str,
    static_summary: str,
    max_code_chars: int = 8000,
) -> str:
    """Build the user-turn prompt for complexity analysis."""
    truncated_code = code[:max_code_chars]
    if len(code) > max_code_chars:
        truncated_note = f"\n[Code truncated to {max_code_chars} characters for analysis]"
    else:
        truncated_note = ""

    return f"""Analyze the following {language} source code for algorithmic complexity.

STATIC ANALYSIS FINDINGS (treat as preliminary evidence, not ground truth):
{static_summary}

SOURCE CODE ({language}):
```
{truncated_code}
```{truncated_note}

Provide your analysis as JSON matching the schema in the system prompt.
Focus on:
1. The actual algorithmic structure of the code.
2. Time complexity with clear justification.
3. Space complexity (auxiliary space, excluding input).
4. Best, average, and worst cases where they meaningfully differ.
5. Specific, actionable optimization suggestions if any.
6. Any assumptions required (e.g., input is sorted, n is the array length).
7. Whether you agree with the static analysis findings.

Return only the JSON object."""
