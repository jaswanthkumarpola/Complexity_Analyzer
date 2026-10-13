"""
Language detection module.
Uses layered detection: extension → keyword heuristics → pygments → fallback.
"""
from __future__ import annotations

import os
from typing import Optional, Tuple

from app.api.schemas import ConfidenceLevel, DetectionMethod
from app.core.language_registry import (
    LanguageDefinition,
    all_languages,
    get_language,
    get_language_by_extension,
)


def detect_language(
    code: str,
    filename: Optional[str] = None,
    user_selected: Optional[str] = None,
) -> Tuple[LanguageDefinition, DetectionMethod, ConfidenceLevel]:
    """
    Detect the programming language of the submitted source code.

    Priority order:
    1. user_selected (explicit override)
    2. file extension
    3. keyword heuristics (reliable for common languages)
    4. pygments lexer analysis (supplementary — guess_lexer is unreliable for short snippets)
    5. generic fallback

    Returns (LanguageDefinition, DetectionMethod, ConfidenceLevel).
    """

    # 1. User-selected override
    if user_selected:
        lang = get_language(user_selected)
        if lang:
            return lang, DetectionMethod.USER_SELECTED, ConfidenceLevel.HIGH

    # 2. File extension (high confidence)
    if filename:
        ext = os.path.splitext(filename)[1].lstrip(".")
        lang = get_language_by_extension(ext)
        if lang and lang.identifier != "generic":
            return lang, DetectionMethod.EXTENSION, ConfidenceLevel.HIGH

    # 3. Keyword heuristics (more reliable than guess_lexer for typical source code)
    heuristic_lang, heuristic_conf = _keyword_heuristics(code)
    if heuristic_lang and heuristic_conf in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM):
        return heuristic_lang, DetectionMethod.HEURISTIC, heuristic_conf

    # 4. Pygments-based detection (last resort — often misidentifies short snippets)
    pyg_lang, pyg_conf = _pygments_detect(code)
    if pyg_lang and pyg_conf in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM):
        return pyg_lang, DetectionMethod.PYGMENTS, pyg_conf

    # 5. Low-confidence heuristic result is still better than nothing
    if heuristic_lang:
        return heuristic_lang, DetectionMethod.HEURISTIC, heuristic_conf

    # 6. Generic fallback
    generic = get_language("generic")
    assert generic is not None
    return generic, DetectionMethod.UNKNOWN, ConfidenceLevel.UNKNOWN


def _pygments_detect(
    code: str,
) -> Tuple[Optional[LanguageDefinition], ConfidenceLevel]:
    """
    Use Pygments to guess the lexer from code content.

    Note: pygments.guess_lexer is known to be unreliable for short or
    ambiguous snippets. This is used only as a supplementary signal.
    """
    try:
        from pygments.lexers import guess_lexer

        lexer = guess_lexer(code)
        lexer_name = type(lexer).__name__.lower()

        # Only accept if the name contains a known language token
        # (exact match to avoid partial collisions like 'c' in 'scdoclexer')
        for lang_def in all_languages():
            if not lang_def.pygments_lexer:
                continue
            stored = lang_def.pygments_lexer.lower()
            if stored == lexer_name:
                return lang_def, ConfidenceLevel.MEDIUM

        return None, ConfidenceLevel.UNKNOWN
    except Exception:
        return None, ConfidenceLevel.UNKNOWN


def _keyword_heuristics(
    code: str,
) -> Tuple[Optional[LanguageDefinition], ConfidenceLevel]:
    """
    Score each language by how many of its distinctive keywords appear.
    Return the best-scoring language when the evidence is clear enough.

    Scoring rules:
    - Each keyword match scores 1 point for that language.
    - The winning language must have ≥40% of total points AND ≥1 match.
    - Confidence is High (≥3 matches), Medium (2), or Low (1).
    """
    scores: dict[str, int] = {}

    for lang_def in all_languages():
        if not lang_def.keywords or lang_def.identifier == "generic":
            continue
        score = sum(1 for kw in lang_def.keywords if kw in code)
        if score > 0:
            scores[lang_def.identifier] = score

    if not scores:
        return None, ConfidenceLevel.UNKNOWN

    best_id = max(scores, key=lambda k: scores[k])
    best_score = scores[best_id]
    total = sum(scores.values())

    share = best_score / total if total > 0 else 0
    if share < 0.4 or best_score < 1:
        return None, ConfidenceLevel.UNKNOWN

    lang = get_language(best_id)
    if not lang:
        return None, ConfidenceLevel.UNKNOWN

    if best_score >= 3:
        confidence = ConfidenceLevel.HIGH
    elif best_score >= 2:
        confidence = ConfidenceLevel.MEDIUM
    else:
        confidence = ConfidenceLevel.LOW

    return lang, confidence
