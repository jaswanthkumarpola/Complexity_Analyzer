from __future__ import annotations

import ast
import textwrap
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LoopInfo:
    loop_type: str           # "for" | "while"
    lineno: int
    nest_depth: int
    has_break: bool = False
    bound_hint: Optional[str] = None   # e.g. "n", "len(arr)", unknown


@dataclass
class RecursionInfo:
    function_name: str
    call_sites: List[int] = field(default_factory=list)   # line numbers
    is_multiple: bool = False   # multiple recursive calls in one path


@dataclass
class ParseResult:
    success: bool
    parse_errors: List[str] = field(default_factory=list)
    loops: List[LoopInfo] = field(default_factory=list)
    nested_loops: List[Dict[str, Any]] = field(default_factory=list)
    recursive_functions: List[RecursionInfo] = field(default_factory=list)
    function_names: List[str] = field(default_factory=list)
    has_sorting: bool = False
    has_binary_search: bool = False
    has_divide_conquer: bool = False
    memory_allocs: List[Dict[str, Any]] = field(default_factory=list)
    library_calls: List[str] = field(default_factory=list)
    dominant_ops: List[str] = field(default_factory=list)
    input_variables: List[str] = field(default_factory=list)
    has_early_exit: bool = False
    max_nest_depth: int = 0


# Known stdlib sorting / searching / data-structure calls
_SORT_CALLS = {"sorted", "sort", "heapq.heappush", "heapq.heappop", "bisect"}
_SEARCH_CALLS = {"bisect.bisect", "bisect_left", "bisect_right"}
_ALLOC_CALLS = {"list", "dict", "set", "defaultdict", "deque", "heapq", "array"}
_KNOWN_COMPLEXITIES = {
    "sorted": "O(n log n)",
    "sort": "O(n log n) (in-place Timsort)",
    "bisect_left": "O(log n)",
    "bisect_right": "O(log n)",
    "bisect": "O(log n)",
}


class _FeatureVisitor(ast.NodeVisitor):
    """Walk Python AST and collect complexity-relevant features."""

    def __init__(self) -> None:
        self.loops: List[LoopInfo] = []
        self._nest_depth: int = 0
        self.max_nest_depth: int = 0
        self.nested_loops: List[Dict[str, Any]] = []
        self.function_names: List[str] = []
        self._function_bodies: Dict[str, ast.FunctionDef] = {}
        self.recursive_functions: List[RecursionInfo] = []
        self.has_sorting = False
        self.has_binary_search = False
        self.has_divide_conquer = False
        self.memory_allocs: List[Dict[str, Any]] = []
        self.library_calls: List[str] = []
        self.dominant_ops: List[str] = []
        self.has_early_exit = False
        self._current_func: Optional[str] = None
        self._recursive_calls: Dict[str, List[int]] = {}

    # -------- Functions --------

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # type: ignore[override]
        self.function_names.append(node.name)
        self._function_bodies[node.name] = node
        prev = self._current_func
        self._current_func = node.name
        self.generic_visit(node)
        self._current_func = prev

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    # -------- Loops --------

    def _enter_loop(self, node: ast.AST, loop_type: str, bound_hint: Optional[str]) -> None:
        self._nest_depth += 1
        if self._nest_depth > self.max_nest_depth:
            self.max_nest_depth = self._nest_depth

        has_break = any(
            isinstance(child, ast.Break)
            for child in ast.walk(node)  # type: ignore[arg-type]
        )
        li = LoopInfo(
            loop_type=loop_type,
            lineno=node.lineno,  # type: ignore[attr-defined]
            nest_depth=self._nest_depth,
            has_break=has_break,
            bound_hint=bound_hint,
        )
        self.loops.append(li)
        if self._nest_depth >= 2:
            self.nested_loops.append({
                "depth": self._nest_depth,
                "lineno": node.lineno,  # type: ignore[attr-defined]
                "loop_type": loop_type,
            })
        self.generic_visit(node)
        self._nest_depth -= 1

    def visit_For(self, node: ast.For) -> None:  # type: ignore[override]
        bound = _extract_iter_bound(node.iter)
        self._enter_loop(node, "for", bound)

    def visit_While(self, node: ast.While) -> None:  # type: ignore[override]
        self._enter_loop(node, "while", None)

    # -------- Calls --------

    def visit_Call(self, node: ast.Call) -> None:  # type: ignore[override]
        call_name = _get_call_name(node)
        if call_name:
            # Sorting
            if any(s in call_name for s in ("sort", "sorted", "heapify")):
                self.has_sorting = True
                self.dominant_ops.append(f"Sort call: {call_name}")
            # Binary search / bisect
            if any(s in call_name for s in ("bisect", "binary_search")):
                self.has_binary_search = True
            # Recursion detection
            if self._current_func and call_name == self._current_func:
                self._recursive_calls.setdefault(self._current_func, []).append(
                    node.lineno
                )
            # Known library calls
            for lib_call, complexity in _KNOWN_COMPLEXITIES.items():
                if lib_call in call_name:
                    self.library_calls.append(f"{call_name} ≈ {complexity}")
            # Memory allocations
            for alloc in _ALLOC_CALLS:
                if call_name.endswith(alloc):
                    self.memory_allocs.append({"call": call_name, "lineno": node.lineno})
        self.generic_visit(node)

    # -------- Control flow --------

    def visit_Return(self, node: ast.Return) -> None:  # type: ignore[override]
        self.has_early_exit = True
        self.generic_visit(node)

    def visit_Break(self, node: ast.Break) -> None:  # type: ignore[override]
        self.has_early_exit = True
        self.generic_visit(node)

    # -------- Post-processing --------

    def finalize(self) -> None:
        """Build recursion info after full traversal."""
        for func_name, call_lines in self._recursive_calls.items():
            ri = RecursionInfo(
                function_name=func_name,
                call_sites=call_lines,
                is_multiple=len(call_lines) >= 2,
            )
            self.recursive_functions.append(ri)
            # Multiple recursive calls → divide & conquer / exponential
            if ri.is_multiple:
                self.has_divide_conquer = True

        # Detect binary search by function name convention
        bs_names = {"binary_search", "bsearch", "bin_search", "binary_find"}
        if any(name.lower() in bs_names or "binary" in name.lower()
               for name in self.function_names):
            self.has_binary_search = True


def _get_call_name(node: ast.Call) -> Optional[str]:
    """Extract a dotted call name from an ast.Call node."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        if isinstance(node.func.value, ast.Name):
            return f"{node.func.value.id}.{node.func.attr}"
        return node.func.attr
    return None


def _extract_iter_bound(iter_node: ast.expr) -> Optional[str]:
    """Guess the iterable bound description for a for-loop's iterator."""
    try:
        if isinstance(iter_node, ast.Call):
            call_name = _get_call_name(iter_node)
            if call_name == "range" and iter_node.args:
                return ast.unparse(iter_node.args[-1])
            if call_name in ("enumerate", "zip", "map", "filter", "reversed"):
                if iter_node.args:
                    return ast.unparse(iter_node.args[0])
        if isinstance(iter_node, (ast.Name, ast.Attribute, ast.Subscript)):
            return ast.unparse(iter_node)
    except Exception:
        pass
    return None


def parse_python(code: str) -> ParseResult:
    """
    Parse Python source code and extract structural complexity features.

    Returns a ParseResult with success=False and parse_errors populated
    if the code is syntactically invalid.
    """
    # Normalize indentation
    code = textwrap.dedent(code)

    result = ParseResult(success=False)
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        result.parse_errors.append(f"SyntaxError at line {exc.lineno}: {exc.msg}")
        return result

    visitor = _FeatureVisitor()
    visitor.visit(tree)
    visitor.finalize()

    result.success = True
    result.loops = visitor.loops
    result.nested_loops = visitor.nested_loops
    result.recursive_functions = visitor.recursive_functions
    result.function_names = visitor.function_names
    result.has_sorting = visitor.has_sorting
    result.has_binary_search = visitor.has_binary_search
    result.has_divide_conquer = visitor.has_divide_conquer
    result.memory_allocs = visitor.memory_allocs
    result.library_calls = visitor.library_calls
    result.dominant_ops = visitor.dominant_ops
    result.has_early_exit = visitor.has_early_exit
    result.max_nest_depth = visitor.max_nest_depth

    # Detect input size variable names (common patterns)
    result.input_variables = _guess_input_variables(code)

    return result


def _guess_input_variables(code: str) -> List[str]:
    """Heuristic: find commonly named input-size parameters."""
    common = ["n", "m", "k", "size", "length", "count"]
    found = []
    for name in common:
        # Look for it as a function parameter or assignment target
        if f"def " in code and f"({name}" in code or f", {name}" in code:
            found.append(name)
        elif f" {name} " in code or f"({name})" in code:
            found.append(name)
    return list(dict.fromkeys(found))  # deduplicate, preserve order
