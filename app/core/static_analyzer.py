"""
Generic heuristic static analyzer for languages without a dedicated AST parser.
Uses regex and token-level patterns to identify structural features.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GenericAnalysisResult:
    """Heuristic analysis output for non-Python languages."""
    loops: List[Dict[str, Any]] = field(default_factory=list)
    nested_loops: List[Dict[str, Any]] = field(default_factory=list)
    recursive_hints: List[str] = field(default_factory=list)
    has_sorting: bool = False
    has_binary_search: bool = False
    has_divide_conquer: bool = False
    memory_allocs: List[Dict[str, Any]] = field(default_factory=list)
    library_calls: List[str] = field(default_factory=list)
    dominant_ops: List[str] = field(default_factory=list)
    input_variables: List[str] = field(default_factory=list)
    has_early_exit: bool = False
    max_nest_depth: int = 0
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Language-specific loop keyword sets
# ---------------------------------------------------------------------------

_LOOP_KEYWORDS = {
    "javascript": (r"\b(for|while|forEach|map|filter|reduce)\b", r"\b(break|return)\b"),
    "typescript": (r"\b(for|while|forEach|map|filter|reduce)\b", r"\b(break|return)\b"),
    "java":       (r"\b(for|while|do)\b", r"\b(break|return|continue)\b"),
    "cpp":        (r"\b(for|while|do)\b", r"\b(break|return|continue)\b"),
    "c":          (r"\b(for|while|do)\b", r"\b(break|return|continue)\b"),
    "csharp":     (r"\b(for|foreach|while|do)\b", r"\b(break|return)\b"),
    "go":         (r"\bfor\b", r"\b(break|return|continue)\b"),
    "rust":       (r"\b(for|while|loop)\b", r"\b(break|return|continue)\b"),
    "kotlin":     (r"\b(for|while|forEach|repeat)\b", r"\b(break|return)\b"),
    "swift":      (r"\b(for|while|repeat)\b", r"\b(break|return|continue)\b"),
    "ruby":       (r"\b(for|while|each|map|times|upto|downto|loop)\b", r"\b(break|return|next)\b"),
    "php":        (r"\b(for|foreach|while|do)\b", r"\b(break|return|continue)\b"),
    "scala":      (r"\b(for|while|foreach|map|foldLeft|foldRight)\b", r"\b(return)\b"),
    "r":          (r"\b(for|while|repeat|apply|lapply|sapply|vapply)\b", r"\b(break|next)\b"),
    "julia":      (r"\b(for|while)\b", r"\b(break|return|continue)\b"),
    "dart":       (r"\b(for|while|forEach)\b", r"\b(break|return|continue)\b"),
    "lua":        (r"\b(for|while|repeat)\b", r"\b(break|return)\b"),
    "perl":       (r"\b(for|foreach|while|until|do)\b", r"\b(last|next|return)\b"),
    "haskell":    (r"\b(map|foldr|foldl|iterate|mapM|forM)\b", r""),
    "bash":       (r"\b(for|while|until)\b", r"\b(break|return|continue)\b"),
    "sql":        (r"\b(JOIN|CURSOR|LOOP|WHILE)\b", r""),
    "generic":    (r"\b(for|while|loop|each|foreach|repeat)\b", r"\b(break|return|continue)\b"),
}

_SORT_PATTERNS = re.compile(
    r"\b(sort|sorted|qsort|Arrays\.sort|Collections\.sort|std::sort|"
    r"Array\.sort|np\.sort|orderBy|ORDER BY)\b",
    re.IGNORECASE,
)
_BINARY_SEARCH_PATTERNS = re.compile(
    r"\b(binary.?search|bisect|bsearch|Arrays\.binarySearch|"
    r"Collections\.binarySearch|lower_bound|upper_bound)\b",
    re.IGNORECASE,
)
_DIVIDE_PATTERNS = re.compile(
    r"\b(merge.?sort|quick.?sort|divide|conquer|mid\s*=|n\s*/\s*2|"
    r"mid\s*/\s*2|left.*right|right.*left)\b",
    re.IGNORECASE,
)
_ALLOC_PATTERNS = re.compile(
    r"\b(malloc|calloc|realloc|new\s+\w+|ArrayList|HashMap|HashSet|"
    r"vector<|map<|set<|unordered_map|List\(|dict\(|set\()\b"
)
_RECURSION_NAME_RE = re.compile(
    r"\bdef\s+(\w+)\b|\bfunction\s+(\w+)\b|\bvoid\s+(\w+)\b|\bint\s+(\w+)\b"
    r"|\bpublic\s+\w+\s+(\w+)\b|\bfun\s+(\w+)\b"
)


def analyze_generic(code: str, language: str = "generic") -> GenericAnalysisResult:
    """
    Perform heuristic static analysis on source code without a formal parser.

    Detects loop structures, recursion hints, sorting/searching patterns,
    and memory allocations via regex-based pattern matching.
    """
    result = GenericAnalysisResult()
    lines = code.splitlines()

    # Pick loop regex for language
    lang_key = language if language in _LOOP_KEYWORDS else "generic"
    loop_pattern_str, exit_pattern_str = _LOOP_KEYWORDS[lang_key]
    loop_re = re.compile(loop_pattern_str, re.IGNORECASE)
    exit_re = re.compile(exit_pattern_str, re.IGNORECASE) if exit_pattern_str else None

    # Nest depth tracking: count loop keywords per line, maintain depth stack
    depth = 0
    loop_stack: List[int] = []   # stack of nest depths for open loops

    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//", "/*", "*", "--")):
            continue

        if loop_re.search(line):
            depth += 1
            loop_stack.append(depth)
            if depth > result.max_nest_depth:
                result.max_nest_depth = depth

            loop_info = {
                "lineno": lineno,
                "depth": depth,
                "line_content": stripped[:80],
            }
            result.loops.append(loop_info)
            if depth >= 2:
                result.nested_loops.append(loop_info)

        # Simple depth decrement heuristic for languages that use closing braces
        if re.search(r"^\}|^end\b|^done\b|^fi\b|^esac\b", stripped, re.IGNORECASE):
            if loop_stack:
                loop_stack.pop()
                depth = max(0, depth - 1)

        if exit_re and exit_re.search(line):
            result.has_early_exit = True

    # Global patterns
    if _SORT_PATTERNS.search(code):
        result.has_sorting = True
        result.dominant_ops.append("Sort operation detected")
    if _BINARY_SEARCH_PATTERNS.search(code):
        result.has_binary_search = True
        result.dominant_ops.append("Binary search pattern detected")
    if _DIVIDE_PATTERNS.search(code):
        result.has_divide_conquer = True
        result.dominant_ops.append("Divide-and-conquer pattern detected")

    # Memory allocations
    for m in _ALLOC_PATTERNS.finditer(code):
        result.memory_allocs.append({"pattern": m.group(), "pos": m.start()})

    # Recursion hinting: find function names, then check if they appear in body
    func_names = set()
    for m in _RECURSION_NAME_RE.finditer(code):
        name = next(filter(None, m.groups()), None)
        if name:
            func_names.add(name)
    for name in func_names:
        # Count how many times the name appears as a call (rough)
        call_count = len(re.findall(rf"\b{re.escape(name)}\s*\(", code))
        # definition + at least one call = recursive hint
        if call_count >= 2:
            result.recursive_hints.append(name)
            if call_count >= 3:
                result.has_divide_conquer = True

    # Guess input variables
    result.input_variables = _guess_input_vars(code)

    if result.max_nest_depth == 0 and not result.loops:
        result.warnings.append("No loop structures detected by heuristics.")

    return result


def _guess_input_vars(code: str) -> List[str]:
    """Find common input-size variable names."""
    candidates = ["n", "m", "k", "N", "M", "size", "length", "count", "len"]
    return [c for c in candidates if re.search(rf"\b{c}\b", code)]
