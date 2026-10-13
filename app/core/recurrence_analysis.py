"""
Visualization data generator.
Produces normalized growth curve data for the complexity chart.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from app.api.schemas import VisualizationData

# Canonical complexity classes and their labels
_COMPLEXITY_CURVES: Dict[str, Tuple[str, callable]] = {
    "O(1)":        ("Constant",        lambda n: 1.0),
    "O(log n)":    ("Logarithmic",     lambda n: math.log2(max(n, 1))),
    "O(n)":        ("Linear",          lambda n: float(n)),
    "O(n log n)":  ("Linearithmic",    lambda n: n * math.log2(max(n, 1))),
    "O(n²)":       ("Quadratic",       lambda n: float(n ** 2)),
    "O(n³)":       ("Cubic",           lambda n: float(n ** 3)),
    "O(2ⁿ)":       ("Exponential",     lambda n: float(2 ** min(n, 30))),
    "O(n!)":       ("Factorial",       lambda n: float(math.factorial(min(int(n), 12)))),
}

# Alternative spellings / AI output normalizations
_ALIAS_MAP: Dict[str, str] = {
    "o(1)": "O(1)",
    "o(log n)": "O(log n)",
    "o(logn)": "O(log n)",
    "o(n)": "O(n)",
    "o(nlogn)": "O(n log n)",
    "o(n log n)": "O(n log n)",
    "o(n*log n)": "O(n log n)",
    "o(n^2)": "O(n²)",
    "o(n²)": "O(n²)",
    "o(n2)": "O(n²)",
    "o(n^3)": "O(n³)",
    "o(n³)": "O(n³)",
    "o(2^n)": "O(2ⁿ)",
    "o(2ⁿ)": "O(2ⁿ)",
    "o(n!)": "O(n!)",
}

_N_VALUES = [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]


def normalize_expression(expr: str) -> Optional[str]:
    """Normalize a complexity expression string to a canonical key."""
    key = expr.strip().lower()
    if key in _ALIAS_MAP:
        return _ALIAS_MAP[key]
    # Try direct match in curves
    for canonical in _COMPLEXITY_CURVES:
        if canonical.lower() == key:
            return canonical
    return None


def build_visualization(predicted_expression: Optional[str]) -> VisualizationData:
    """
    Build VisualizationData containing growth curves and optional highlighting.

    If predicted_expression maps to a known curve, it is highlighted.
    The data is normalized so that O(n) at n=1024 = 1.0 for readability.
    """
    canonical = normalize_expression(predicted_expression or "")

    # Compute raw values for all curves
    raw: Dict[str, List[float]] = {}
    for label, (_, fn) in _COMPLEXITY_CURVES.items():
        try:
            raw[label] = [fn(n) for n in _N_VALUES]
        except Exception:
            raw[label] = [0.0] * len(_N_VALUES)

    # Normalize using linear O(n) at max n as the reference
    n_max = _N_VALUES[-1]
    reference = float(n_max)  # O(n) at n_max

    curves: Dict[str, List[float]] = {}
    for label, values in raw.items():
        try:
            normalized = [min(v / reference, 1e6) for v in values]
        except ZeroDivisionError:
            normalized = values
        curves[label] = normalized

    predicted_label = None
    if canonical and canonical in _COMPLEXITY_CURVES:
        predicted_label = _COMPLEXITY_CURVES[canonical][0]

    return VisualizationData(
        predicted_class=canonical,
        predicted_class_label=predicted_label,
        x_values=[float(n) for n in _N_VALUES],
        curves=curves,
        highlight_curve=canonical,
        x_axis_label="Input size (n)",
        y_axis_label="Relative growth (normalized to O(n) at n=1024)",
        disclaimer=(
            "This chart illustrates asymptotic growth rates only. "
            "It does not represent measured execution time, wall-clock performance, "
            "or the constant factors in the Big-O notation."
        ),
    )
