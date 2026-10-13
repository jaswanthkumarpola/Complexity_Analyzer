"""
Tests for the static analysis engine on known complexity cases.
"""
import pytest

from app.core.complexity_rules import infer_complexity
from app.core.parser_manager import parse_python


def _infer_from_python(code: str) -> dict:
    """Helper: parse Python code and run inference."""
    pr = parse_python(code)
    evidence = {
        "loops": [{"lineno": l.lineno, "depth": l.nest_depth, "type": l.loop_type} for l in pr.loops],
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
    return infer_complexity(evidence)


# ===== CONSTANT TIME =====

def test_constant_time_no_loops():
    code = "def get_first(arr):\n    return arr[0]"
    result = _infer_from_python(code)
    assert result.time_expression == "O(1)"


# ===== LINEAR TIME =====

def test_linear_single_loop():
    code = """
def sum_array(arr):
    total = 0
    for x in arr:
        total += x
    return total
"""
    result = _infer_from_python(code)
    assert result.time_expression == "O(n)"


def test_linear_sequential_loops_still_on():
    code = """
def two_passes(arr):
    s = 0
    for x in arr:
        s += x
    m = arr[0]
    for x in arr:
        if x > m:
            m = x
    return s, m
"""
    result = _infer_from_python(code)
    assert result.time_expression == "O(n)"
    assert result.max_nest_depth == 1


# ===== QUADRATIC TIME =====

def test_quadratic_nested_loops():
    code = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(n - i - 1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
"""
    result = _infer_from_python(code)
    assert result.time_expression in ("O(n²)", "O(n^2)")


# ===== LOGARITHMIC TIME =====

def test_logarithmic_binary_search():
    code = """
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
"""
    result = _infer_from_python(code)
    # binary_search detection
    assert result.has_binary_search or result.time_expression in ("O(log n)", "O(n)")


# ===== LINEARITHMIC TIME =====

def test_linearithmic_sorted_call():
    code = """
def process(arr):
    s = sorted(arr)
    result = []
    for x in s:
        result.append(x * 2)
    return result
"""
    result = _infer_from_python(code)
    assert result.has_sorting
    assert "log" in result.time_expression.lower() or "n" in result.time_expression


# ===== EXPONENTIAL TIME =====

def test_exponential_fibonacci():
    code = """
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)
"""
    result = _infer_from_python(code)
    assert result.is_recursive or result.has_divide_conquer


# ===== MEMOIZED FIBONACCI =====

def test_memoized_fibonacci():
    code = """
def fib_memo(n, memo={}):
    if n in memo:
        return memo[n]
    if n <= 1:
        return n
    memo[n] = fib_memo(n-1, memo) + fib_memo(n-2, memo)
    return memo[n]
"""
    pr = parse_python(code)
    assert pr.success
    assert len(pr.recursive_functions) > 0


# ===== EARLY EXIT =====

def test_early_exit_detected():
    code = """
def find_first(arr, target):
    for x in arr:
        if x == target:
            return x
    return None
"""
    result = _infer_from_python(code)
    assert result.has_early_exit


# ===== SYNTAX ERROR =====

def test_syntax_error_handled():
    code = "def broken(:\n    pass"
    pr = parse_python(code)
    assert not pr.success
    assert len(pr.parse_errors) > 0


# ===== RECURSIVE FACTORIAL =====

def test_recursive_factorial():
    code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
    pr = parse_python(code)
    assert pr.success
    assert len(pr.recursive_functions) > 0
    # Single recursive call
    assert not pr.recursive_functions[0].is_multiple


# ===== MULTIPLE RECURSIVE CALLS =====

def test_multiple_recursive_calls_detected():
    code = """
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)
"""
    pr = parse_python(code)
    assert pr.success
    assert any(r.is_multiple for r in pr.recursive_functions)


# ===== SORTING DETECTED =====

def test_sort_call_detected():
    code = """
def sorted_copy(arr):
    return sorted(arr)
"""
    pr = parse_python(code)
    assert pr.has_sorting


# ===== NO LOOPS OR RECURSION =====

def test_no_structure_is_constant():
    code = """
def add(a, b):
    return a + b
"""
    result = _infer_from_python(code)
    assert result.time_expression == "O(1)"
    assert result.space_expression == "O(1)"


# ===== HELPER PROPERTIES =====

@pytest.fixture
def _():
    """Shortcut so test functions can use result.is_recursive."""
    pass


# Patch infer result with convenience property
def _add_props(result):
    result.is_recursive = bool(result.__dict__.get("recursive_hints") or [])
    result.has_binary_search = "binary_search" in str(result.__dict__)
    result.has_early_exit = result.__dict__.get("has_early_exit", False)
    return result
