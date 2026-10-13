"""
Core analysis pipeline. Orchestrates all analysis steps:
1. Validate input
2. Detect language
3. Parse / static-analyze
4. Apply complexity rules
5. Call AI provider
6. Reconcile results
7. Build response
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.ai.base_provider import AIAnalysisResult
from app.ai.provider_factory import get_provider
from app.api.schemas import (
    AnalysisMethod,
    AnalysisResponse,
    AnalysisSettings,
    BoundType,
    CaseComplexity,
    ComplexityEstimate,
    ConfidenceLevel,
    DetectionMethod,
    LanguageInfo,
    OptimizationSuggestion,
    ProviderStatus,
    StaticEvidence,
)
from app.core.complexity_rules import infer_complexity
from app.core.language_detection import detect_language
from app.core.language_registry import LanguageDefinition
from app.core.recurrence_analysis import build_visualization
from app.core.static_analyzer import analyze_generic
from app.utils.errors import ProviderError

logger = logging.getLogger(__name__)


async def run_analysis(
    code: str,
    language_override: Optional[str] = None,
    filename: Optional[str] = None,
    settings: Optional[AnalysisSettings] = None,
) -> AnalysisResponse:
    """
    Execute the full complexity analysis pipeline.

    Parameters
    ----------
    code : str
        Source code submitted by the user (already validated for size).
    language_override : Optional[str]
        User-selected language identifier; takes priority over detection.
    filename : Optional[str]
        Original file name, used to assist language detection.
    settings : Optional[AnalysisSettings]
        Analysis configuration knobs.
    """
    if settings is None:
        settings = AnalysisSettings()

    warnings: List[str] = []
    limitations: List[str] = []

    # ------------------------------------------------------------------
    # Step 1: Language detection
    # ------------------------------------------------------------------
    lang_def, detect_method, detect_conf = detect_language(
        code, filename=filename, user_selected=language_override
    )
    lang_info = LanguageInfo(
        identifier=lang_def.identifier,
        display_name=lang_def.display_name,
        detection_method=detect_method,
        detection_confidence=detect_conf,
        parser_available=lang_def.parser_available,
        static_analysis_available=lang_def.static_analysis,
        known_limitations=lang_def.known_limitations,
    )
    limitations.extend(lang_def.known_limitations)

    # ------------------------------------------------------------------
    # Step 2: Parse / static-analyze
    # ------------------------------------------------------------------
    static_evidence, evidence_dict = _run_parser(lang_def, code, warnings)

    # ------------------------------------------------------------------
    # Step 3: Rule-based complexity inference
    # ------------------------------------------------------------------
    inference = infer_complexity(evidence_dict)
    warnings.extend(inference.warnings)

    # ------------------------------------------------------------------
    # Step 4: Build static summary for AI prompt
    # ------------------------------------------------------------------
    static_summary = _build_static_summary(inference, evidence_dict, lang_def)

    # ------------------------------------------------------------------
    # Step 5: AI provider
    # ------------------------------------------------------------------
    # get_provider() raises ProviderError if the AI is misconfigured (no silent mock).
    provider = get_provider()
    provider_error: Optional[str] = None

    try:
        ai_result: AIAnalysisResult = await provider.analyze(
            code, lang_def.display_name, static_summary
        )
    except ProviderError:
        raise  # readable message, surfaced to the user by the API layer
    except Exception as exc:
        logger.error("Unexpected AI provider failure: %s", exc, exc_info=True)
        raise ProviderError(
            f"AI analysis failed unexpectedly: {type(exc).__name__}: {exc}", status_code=502
        ) from exc

    # ------------------------------------------------------------------
    # Step 6: Reconcile results
    # ------------------------------------------------------------------
    time_complex, space_complex, case_analysis, optimizations, confidence, method = _reconcile(
        inference, ai_result, provider, provider_error, warnings
    )

    # ------------------------------------------------------------------
    # Step 7: Build visualization
    # ------------------------------------------------------------------
    viz = None
    if settings.include_visualization:
        viz = build_visualization(time_complex.expression)

    provider_status = ProviderStatus(
        provider=provider.provider_name,
        model=ai_result.model if ai_result else None,
        ai_used=ai_result is not None and not ai_result.is_fallback,
        fallback_reason=provider_error,
    )

    # Collect explanation
    explanation = ""
    if ai_result:
        explanation = ai_result.explanation
    if not explanation:
        explanation = inference.time_justification or "(No explanation available.)"

    assumptions = []
    if ai_result:
        assumptions.extend(ai_result.assumptions)
    assumptions.extend(inference.time_assumptions)
    assumptions = list(dict.fromkeys(assumptions))  # deduplicate

    return AnalysisResponse(
        language=lang_info,
        analysis_method=method,
        provider_status=provider_status,
        time_complexity=time_complex,
        space_complexity=space_complex,
        case_analysis=case_analysis,
        static_evidence=static_evidence,
        explanation=explanation[:4000],
        assumptions=assumptions[:10],
        confidence=confidence,
        optimizations=optimizations,
        visualization=viz,
        warnings=list(set(warnings))[:10],
        limitations=list(set(limitations))[:10],
    )
# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _run_parser(
    lang_def: LanguageDefinition, code: str, warnings: List[str]
) -> tuple[StaticEvidence, Dict[str, Any]]:
    """Run the appropriate parser or fall back to generic heuristics."""

    if lang_def.identifier == "python" and lang_def.parser_available:
        from app.core.parser_manager import parse_python
        pr = parse_python(code)

        if not pr.success:
            warnings.extend(pr.parse_errors)
            warnings.append("Python AST parse failed; falling back to heuristic analysis.")
            return _generic_analysis(lang_def, code, warnings)

        evidence_dict: Dict[str, Any] = {
            "loops": [{"lineno": l.lineno, "depth": l.nest_depth, "type": l.loop_type, "bound": l.bound_hint} for l in pr.loops],
            "nested_loops": pr.nested_loops,
            "recursive_functions": [{"name": r.function_name, "is_multiple": r.is_multiple} for r in pr.recursive_functions],
            "recursive_hints": [r.function_name for r in pr.recursive_functions],
            "has_sorting": pr.has_sorting,
            "has_binary_search": pr.has_binary_search,
            "has_divide_conquer": pr.has_divide_conquer,
            "memory_allocs": pr.memory_allocs,
            "library_calls": pr.library_calls,
            "dominant_ops": pr.dominant_ops,
            "input_variables": pr.input_variables,
            "has_early_exit": pr.has_early_exit,
            "max_nest_depth": pr.max_nest_depth,
        }
        evidence = StaticEvidence(
            loops=evidence_dict["loops"],
            nested_loops=pr.nested_loops,
            recursive_calls=[{"name": r.function_name, "is_multiple": r.is_multiple, "call_sites": r.call_sites} for r in pr.recursive_functions],
            dominant_operations=pr.dominant_ops,
            input_variables=pr.input_variables,
            library_calls=pr.library_calls,
            memory_allocations=pr.memory_allocs,
            early_exits=pr.has_early_exit,
            has_sorting=pr.has_sorting,
            has_binary_search=pr.has_binary_search,
            has_divide_conquer=pr.has_divide_conquer,
            parser_used="python_ast",
            parse_errors=pr.parse_errors,
        )
        return evidence, evidence_dict

    return _generic_analysis(lang_def, code, warnings)


def _generic_analysis(
    lang_def: LanguageDefinition, code: str, warnings: List[str]
) -> tuple[StaticEvidence, Dict[str, Any]]:
    """Run generic heuristic analysis."""
    gr = analyze_generic(code, lang_def.identifier)
    warnings.extend(gr.warnings)

    evidence_dict: Dict[str, Any] = {
        "loops": gr.loops,
        "nested_loops": gr.nested_loops,
        "recursive_functions": [],
        "recursive_hints": gr.recursive_hints,
        "has_sorting": gr.has_sorting,
        "has_binary_search": gr.has_binary_search,
        "has_divide_conquer": gr.has_divide_conquer,
        "memory_allocs": gr.memory_allocs,
        "library_calls": gr.library_calls,
        "dominant_ops": gr.dominant_ops,
        "input_variables": gr.input_variables,
        "has_early_exit": gr.has_early_exit,
        "max_nest_depth": gr.max_nest_depth,
    }
    evidence = StaticEvidence(
        loops=gr.loops,
        nested_loops=gr.nested_loops,
        recursive_calls=[{"name": r} for r in gr.recursive_hints],
        dominant_operations=gr.dominant_ops,
        input_variables=gr.input_variables,
        library_calls=gr.library_calls,
        memory_allocations=gr.memory_allocs,
        early_exits=gr.has_early_exit,
        has_sorting=gr.has_sorting,
        has_binary_search=gr.has_binary_search,
        has_divide_conquer=gr.has_divide_conquer,
        parser_used="generic_heuristic",
        parse_errors=[],
    )
    return evidence, evidence_dict


def _build_static_summary(inference, evidence_dict: Dict[str, Any], lang_def: LanguageDefinition) -> str:
    """Format static analysis findings for the AI prompt."""
    lines = [
        f"Language: {lang_def.display_name}",
        f"Time complexity: {inference.time_expression}",
        f"Space complexity: {inference.space_expression}",
        f"Best case: {inference.best_case or 'unknown'}",
        f"Average case: {inference.average_case or 'unknown'}",
        f"Worst case: {inference.worst_case or 'unknown'}",
        f"Static confidence: {inference.time_confidence}",
        "",
        f"Loops found: {len(evidence_dict.get('loops', []))}",
        f"Maximum nesting depth: {evidence_dict.get('max_nest_depth', 0)}",
        f"Recursive functions: {evidence_dict.get('recursive_hints', [])}",
        f"Has sorting: {evidence_dict.get('has_sorting', False)}",
        f"Has binary search: {evidence_dict.get('has_binary_search', False)}",
        f"Has divide and conquer: {evidence_dict.get('has_divide_conquer', False)}",
        f"Has early exit: {evidence_dict.get('has_early_exit', False)}",
        f"Input variables: {evidence_dict.get('input_variables', [])}",
        f"Library calls: {evidence_dict.get('library_calls', [])}",
        f"Dominant operations: {evidence_dict.get('dominant_ops', [])}",
    ]
    if inference.time_evidence:
        lines.append("\nTime evidence:")
        lines.extend(f"  - {e}" for e in inference.time_evidence)
    if inference.warnings:
        lines.append("\nWarnings:")
        lines.extend(f"  - {w}" for w in inference.warnings)
    return "\n".join(lines)


def _reconcile(
    inference,
    ai_result: Optional[AIAnalysisResult],
    provider,
    provider_error: Optional[str],
    warnings: List[str],
):
    """Combine static inference and AI result into final response fields."""

    is_ai = ai_result is not None and not ai_result.is_fallback
    is_fallback = ai_result is None or ai_result.is_fallback

    # Determine analysis method
    if is_ai:
        method = AnalysisMethod.AI_ASSISTED
    elif not is_fallback and provider_error:
        method = AnalysisMethod.STATIC_ONLY
        warnings.append("AI provider call failed; results from static analysis only.")
    else:
        method = AnalysisMethod.FALLBACK

    # Time complexity — prefer AI when available, else use static inference
    if ai_result:
        time_expr = ai_result.time_complexity or inference.time_expression
        space_expr = ai_result.space_complexity or inference.space_expression
        ai_conf_map = {"High": ConfidenceLevel.HIGH, "Medium": ConfidenceLevel.MEDIUM,
                       "Low": ConfidenceLevel.LOW, "Unknown": ConfidenceLevel.UNKNOWN}
        conf = ai_conf_map.get(ai_result.confidence, ConfidenceLevel.LOW)
        if is_fallback:
            conf = ConfidenceLevel.LOW
    else:
        time_expr = inference.time_expression
        space_expr = inference.space_expression
        conf = inference.time_confidence

    time_complex = ComplexityEstimate(
        expression=time_expr,
        bound_type=BoundType.BIG_O,
        justification=inference.time_justification,
        confidence=conf,
        evidence=inference.time_evidence,
        assumptions=inference.time_assumptions,
    )
    space_complex = ComplexityEstimate(
        expression=space_expr,
        bound_type=BoundType.BIG_O,
        justification=inference.space_justification,
        confidence=conf if not is_fallback else ConfidenceLevel.LOW,
        evidence=inference.space_evidence,
        assumptions=inference.space_assumptions,
    )

    # Cases
    def _case_estimate(expr: Optional[str]) -> Optional[ComplexityEstimate]:
        if not expr:
            return None
        return ComplexityEstimate(expression=expr, bound_type=BoundType.BIG_O, confidence=conf)

    if ai_result:
        bc = _case_estimate(ai_result.best_case or inference.best_case)
        ac = _case_estimate(ai_result.average_case or inference.average_case)
        wc = _case_estimate(ai_result.worst_case or inference.worst_case)
    else:
        bc = _case_estimate(inference.best_case)
        ac = _case_estimate(inference.average_case)
        wc = _case_estimate(inference.worst_case)

    case_analysis = CaseComplexity(best_case=bc, average_case=ac, worst_case=wc)

    # Optimizations
    optimizations: List[OptimizationSuggestion] = []
    if ai_result and ai_result.optimizations:
        for opt_dict in ai_result.optimizations[:5]:
            if isinstance(opt_dict, dict):
                opt_conf_map = {"High": ConfidenceLevel.HIGH, "Medium": ConfidenceLevel.MEDIUM, "Low": ConfidenceLevel.LOW}
                optimizations.append(OptimizationSuggestion(
                    title=opt_dict.get("title", "Optimization"),
                    issue_description=opt_dict.get("issue_description", ""),
                    evidence=opt_dict.get("evidence", ""),
                    proposed_change=opt_dict.get("proposed_change", ""),
                    time_complexity_impact=opt_dict.get("time_complexity_impact", ""),
                    space_complexity_impact=opt_dict.get("space_complexity_impact", ""),
                    trade_offs=opt_dict.get("trade_offs", ""),
                    confidence=opt_conf_map.get(opt_dict.get("confidence", "Low"), ConfidenceLevel.LOW),
                ))

    return time_complex, space_complex, case_analysis, optimizations, conf, method
