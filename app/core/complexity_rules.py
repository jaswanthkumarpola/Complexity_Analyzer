"""
Rule-based complexity inference.
Converts structural evidence from parsers/analyzers into candidate
complexity classes. Results are evidence-based estimates, not proofs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.api.schemas import BoundType, ComplexityEstimate, ConfidenceLevel


@dataclass
class ComplexityInference:
    """Output of the rule-based complexity inference step."""
    time_expression: str = "O(n)"
    time_bound: BoundType = BoundType.BIG_O
    time_confidence: ConfidenceLevel = ConfidenceLevel.LOW
    time_evidence: List[str] = field(default_factory=list)
    time_justification: str = ""
    time_assumptions: List[str] = field(default_factory=list)

    space_expression: str = "O(1)"
    space_bound: BoundType = BoundType.BIG_O
    space_confidence: ConfidenceLevel = ConfidenceLevel.LOW
    space_evidence: List[str] = field(default_factory=list)
    space_justification: str = ""
    space_assumptions: List[str] = field(default_factory=list)

    best_case: Optional[str] = None
    average_case: Optional[str] = None
    worst_case: Optional[str] = None

    warnings: List[str] = field(default_factory=list)

    # Passthrough evidence fields (set during inference for convenience)
    has_sorting: bool = False
    has_binary_search: bool = False
    has_divide_conquer: bool = False
    is_recursive: bool = False
    has_early_exit: bool = False
    max_nest_depth: int = 0


def infer_complexity(evidence: Dict[str, Any]) -> ComplexityInference:
    """
    Apply structural rules to produce complexity estimates.

    `evidence` contains fields from either the Python AST parser or
    the generic heuristic analyzer, normalized to a common format.
    """
    result = ComplexityInference()
    time_ev: List[str] = []
    space_ev: List[str] = []

    loops: List[Dict[str, Any]] = evidence.get("loops", [])
    nested_loops: List[Dict[str, Any]] = evidence.get("nested_loops", [])
    recursive_fns = evidence.get("recursive_functions", []) or evidence.get("recursive_hints", [])
    has_sorting: bool = evidence.get("has_sorting", False)
    has_binary_search: bool = evidence.get("has_binary_search", False)
    has_divide_conquer: bool = evidence.get("has_divide_conquer", False)
    max_nest_depth: int = evidence.get("max_nest_depth", 0)
    memory_allocs: List[Dict] = evidence.get("memory_allocs", [])
    has_early_exit: bool = evidence.get("has_early_exit", False)
    is_recursive = bool(recursive_fns)

    # Set passthrough evidence fields for external access
    result.has_sorting = has_sorting
    result.has_binary_search = has_binary_search
    result.has_divide_conquer = has_divide_conquer
    result.is_recursive = is_recursive
    result.has_early_exit = has_early_exit
    result.max_nest_depth = max_nest_depth

    # ---------- TIME COMPLEXITY ----------

    # No loops or recursion → O(1) candidate
    if not loops and not is_recursive and not has_sorting:
        result.time_expression = "O(1)"
        result.time_confidence = ConfidenceLevel.HIGH
        time_ev.append("No loops or recursion detected.")
        result.time_justification = (
            "No iterative or recursive structure found; operations appear constant-time."
        )
        result.time_assumptions.append(
            "Assumes all called functions are O(1). If library calls have non-trivial cost, adjust accordingly."
        )
        result.best_case = "O(1)"
        result.average_case = "O(1)"
        result.worst_case = "O(1)"

    # Sorting → at least O(n log n)
    elif has_sorting:
        result.time_expression = "O(n log n)"
        result.time_confidence = ConfidenceLevel.MEDIUM
        time_ev.append("Sort operation detected (likely O(n log n) comparison sort).")
        result.time_justification = (
            "A sorting call was identified. Standard comparison-based sorting is O(n log n). "
            "Combined with any surrounding loops, overall complexity may be higher."
        )
        result.time_assumptions.append("Assumes n is the number of elements being sorted.")
        result.best_case = "O(n log n)"
        result.average_case = "O(n log n)"
        result.worst_case = "O(n log n)"
        if loops:
            result.time_expression = f"O(n log n)" if max_nest_depth < 2 else "O(n² log n)"
            if max_nest_depth >= 2:
                time_ev.append(f"Nested loops (depth {max_nest_depth}) around or adjacent to sort.")

    # Binary search → O(log n) — takes priority over single-loop O(n)
    elif has_binary_search:
        result.time_expression = "O(log n)"
        result.time_confidence = ConfidenceLevel.HIGH
        time_ev.append("Binary search pattern or function detected.")
        result.time_justification = "Binary search halves the search space each iteration → O(log n)."
        result.time_assumptions.append("Assumes sorted input and O(1) element access.")
        result.best_case = "O(1)"
        result.average_case = "O(log n)"
        result.worst_case = "O(log n)"

    # Recursion with multiple recursive calls → exponential candidate
    elif is_recursive and has_divide_conquer:
        # Check if it's likely merge sort style (not truly exponential)
        if has_sorting or any(
            "merge" in str(r).lower() or "sort" in str(r).lower()
            for r in recursive_fns
        ):
            result.time_expression = "O(n log n)"
            result.time_confidence = ConfidenceLevel.MEDIUM
            time_ev.append("Recursive divide-and-conquer with merge/sort pattern detected.")
        else:
            result.time_expression = "O(2ⁿ)"
            result.time_confidence = ConfidenceLevel.LOW
            time_ev.append("Multiple recursive calls per invocation detected.")
            time_ev.append("This is a heuristic; actual complexity depends on the recurrence.")
            result.warnings.append(
                "Multiple recursive calls detected. If memoization or pruning is present, "
                "complexity may be substantially better than O(2ⁿ)."
            )
        result.time_justification = (
            "Recursion with branching detected. Exact complexity requires recurrence analysis."
        )
        result.best_case = "O(n)"  # optimistic
        result.average_case = result.time_expression
        result.worst_case = result.time_expression

    # Single recursion → O(n) candidate
    elif is_recursive and not has_divide_conquer:
        result.time_expression = "O(n)"
        result.time_confidence = ConfidenceLevel.LOW
        time_ev.append("Single recursive call per invocation detected.")
        result.time_justification = (
            "Linear recursion detected. Actual complexity depends on recursion depth "
            "and per-call work."
        )
        result.time_assumptions.append("Assumes recursion depth proportional to n.")
        result.best_case = "O(1)"
        result.average_case = "O(n)"
        result.worst_case = "O(n)"

    # Nested loops
    elif max_nest_depth >= 2:
        depth = max_nest_depth
        expr = f"O(n^{depth})" if depth > 2 else "O(n²)"
        result.time_expression = expr
        result.time_confidence = ConfidenceLevel.HIGH
        time_ev.append(f"Nested loops detected with maximum nesting depth {depth}.")
        result.time_justification = (
            f"Loops nested {depth} levels deep, each likely iterating over input-sized data. "
            "This is a structural estimate; actual complexity depends on loop bounds."
        )
        result.time_assumptions.extend([
            "Assumes each loop iterates O(n) times over input-sized data.",
            "If loop bounds are independent of input or are constant, complexity is lower.",
        ])
        result.best_case = "O(n²)" if depth == 2 else expr
        result.average_case = expr
        result.worst_case = expr
        if has_early_exit:
            result.best_case = "O(1)"
            result.warnings.append(
                "Early exit detected; best-case may be better than stated worst-case."
            )

    # Single or sequential loops → O(n)
    elif loops:
        result.time_expression = "O(n)"
        result.time_confidence = ConfidenceLevel.MEDIUM
        time_ev.append(f"{len(loops)} loop(s) detected with no significant nesting.")
        result.time_justification = (
            "Sequential loops each traversing input-sized data are O(n) in aggregate."
        )
        result.time_assumptions.append(
            "Assumes loop iteration counts are proportional to input size n."
        )
        result.best_case = "O(1)" if has_early_exit else "O(n)"
        result.average_case = "O(n)"
        result.worst_case = "O(n)"

    else:
        result.time_expression = "O(n)"
        result.time_confidence = ConfidenceLevel.LOW
        result.warnings.append(
            "Could not determine complexity with confidence from structure alone."
        )

    # ---------- SPACE COMPLEXITY ----------

    recursive_space = is_recursive
    has_allocs = bool(memory_allocs)
    has_sort_alloc = has_sorting  # merge sort allocates O(n)

    if has_sort_alloc and "merge" in str(recursive_fns).lower():
        result.space_expression = "O(n)"
        space_ev.append("Merge sort requires O(n) auxiliary storage for merge step.")
        result.space_confidence = ConfidenceLevel.MEDIUM
    elif recursive_space:
        depth_est = "n"
        result.space_expression = f"O({depth_est})"
        space_ev.append(f"Recursive calls use O({depth_est}) stack space in worst case.")
        result.space_confidence = ConfidenceLevel.LOW
        result.space_assumptions.append("Assumes recursion depth proportional to n.")
        if has_divide_conquer:
            result.space_expression = "O(n)"
            space_ev.append("Divide-and-conquer recursion stack depth is O(log n) to O(n).")
    elif has_allocs:
        result.space_expression = "O(n)"
        space_ev.append("Dynamic memory allocations detected; auxiliary space may scale with input.")
        result.space_confidence = ConfidenceLevel.LOW
        result.space_assumptions.append("Assumes allocated data structures scale with input size n.")
    else:
        result.space_expression = "O(1)"
        space_ev.append("No significant auxiliary allocations detected.")
        result.space_confidence = ConfidenceLevel.MEDIUM
        result.space_justification = "Only a constant number of variables appear to be allocated."
        result.space_assumptions.append(
            "Excludes input storage; measures auxiliary (extra) space only."
        )

    result.time_evidence = time_ev
    result.space_evidence = space_ev
    return result
